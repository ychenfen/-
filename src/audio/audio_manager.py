"""
音频管理模块
统一管理音频输入输出和音频处理任务
"""

import threading
import time
import queue
from typing import Dict, List, Optional, Callable
import logging
import numpy as np

from .asr import SpeechRecognizer
from .tts import TextToSpeech

class AudioManager:
    def __init__(self, asr_model: str = "small", tts_rate: int = 200):
        """
        初始化音频管理器
        
        Args:
            asr_model: ASR模型名称
            tts_rate: TTS语音速度
        """
        self.logger = logging.getLogger(__name__)
        
        # 初始化ASR和TTS
        try:
            self.asr = SpeechRecognizer(model_name=asr_model, language="zh")
            self.tts = TextToSpeech(voice_rate=tts_rate)
            self.logger.info("音频管理器初始化成功")
        except Exception as e:
            self.logger.error(f"音频管理器初始化失败: {e}")
            raise
        
        # 对话状态管理
        self.conversation_active = False
        self.wake_word_enabled = True
        self.wake_words = ["小助手", "机器人", "你好"]
        
        # 音频处理队列
        self.audio_task_queue = queue.Queue()
        self.processing_thread = None
        self.is_processing = False
        
        # 回调函数管理
        self.speech_recognized_callbacks = []
        self.wake_word_detected_callbacks = []
        self.conversation_started_callbacks = []
        self.conversation_ended_callbacks = []
        
        # 设置内部回调
        self.asr.add_recognition_callback(self._on_speech_recognized)
        self.tts.add_speech_callback(self._on_speech_synthesized)
    
    def start_listening(self) -> bool:
        """
        开始音频监听
        
        Returns:
            是否启动成功
        """
        try:
            # 启动ASR连续识别
            if not self.asr.start_continuous_recognition():
                return False
            
            # 启动音频处理线程
            self._start_processing_thread()
            
            self.logger.info("音频监听开始")
            return True
            
        except Exception as e:
            self.logger.error(f"启动音频监听失败: {e}")
            return False
    
    def stop_listening(self):
        """
        停止音频监听
        """
        try:
            # 停止ASR
            self.asr.stop_continuous_recognition()
            
            # 停止处理线程
            self._stop_processing_thread()
            
            # 停止TTS
            self.tts.stop_speaking()
            
            self.logger.info("音频监听停止")
            
        except Exception as e:
            self.logger.error(f"停止音频监听失败: {e}")
    
    def speak(self, text: str, priority: str = "normal", emotion: str = "neutral") -> bool:
        """
        语音输出
        
        Args:
            text: 要说的文本
            priority: 优先级 ("high", "normal", "low")
            emotion: 情感 ("happy", "sad", "excited", "calm", "neutral")
            
        Returns:
            是否成功添加到输出队列
        """
        if not text.strip():
            return False
        
        try:
            # 高优先级的语音会打断当前语音
            if priority == "high":
                self.tts.stop_speaking()
            
            return self.tts.speak_with_emotion(text, emotion, blocking=False)
            
        except Exception as e:
            self.logger.error(f"语音输出失败: {e}")
            return False
    
    def speak_educational_content(self, content: str, content_type: str = "explanation") -> bool:
        """
        教育内容语音播放
        
        Args:
            content: 教育内容
            content_type: 内容类型
            
        Returns:
            是否成功
        """
        return self.tts.speak_educational_content(content, content_type)
    
    def start_conversation(self):
        """
        开始对话模式
        """
        if not self.conversation_active:
            self.conversation_active = True
            self.wake_word_enabled = False  # 对话模式下禁用唤醒词
            
            # 调用对话开始回调
            for callback in self.conversation_started_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"对话开始回调执行失败: {e}")
            
            self.logger.info("对话模式开始")
    
    def end_conversation(self):
        """
        结束对话模式
        """
        if self.conversation_active:
            self.conversation_active = False
            self.wake_word_enabled = True  # 重新启用唤醒词
            
            # 调用对话结束回调
            for callback in self.conversation_ended_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"对话结束回调执行失败: {e}")
            
            self.logger.info("对话模式结束")
    
    def _on_speech_recognized(self, recognition_result: Dict):
        """
        语音识别回调处理
        
        Args:
            recognition_result: 识别结果
        """
        text = recognition_result.get('text', '').strip()
        confidence = recognition_result.get('confidence', 0.0)
        
        if not text or confidence < -2.0:  # Whisper置信度阈值
            return
        
        self.logger.debug(f"识别到语音: {text}")
        
        # 检查唤醒词
        if self.wake_word_enabled and not self.conversation_active:
            if self._check_wake_word(text):
                # 调用唤醒词检测回调
                for callback in self.wake_word_detected_callbacks:
                    try:
                        callback(text)
                    except Exception as e:
                        self.logger.error(f"唤醒词回调执行失败: {e}")
                
                # 自动开始对话
                self.start_conversation()
                return
        
        # 对话模式下处理语音
        if self.conversation_active:
            # 调用语音识别回调
            for callback in self.speech_recognized_callbacks:
                try:
                    callback(recognition_result)
                except Exception as e:
                    self.logger.error(f"语音识别回调执行失败: {e}")
    
    def _on_speech_synthesized(self, speech_item: Dict):
        """
        语音合成回调处理
        
        Args:
            speech_item: 语音合成任务
        """
        self.logger.debug("语音播放完成")
    
    def _check_wake_word(self, text: str) -> bool:
        """
        检查是否包含唤醒词
        
        Args:
            text: 识别的文本
            
        Returns:
            是否包含唤醒词
        """
        text_lower = text.lower()
        for wake_word in self.wake_words:
            if wake_word.lower() in text_lower:
                self.logger.info(f"检测到唤醒词: {wake_word}")
                return True
        return False
    
    def _start_processing_thread(self):
        """
        启动音频处理线程
        """
        if self.processing_thread and self.processing_thread.is_alive():
            return
        
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._processing_worker)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _stop_processing_thread(self):
        """
        停止音频处理线程
        """
        self.is_processing = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
    
    def _processing_worker(self):
        """
        音频处理工作线程
        """
        while self.is_processing:
            try:
                # 获取音频处理任务
                task = self.audio_task_queue.get(timeout=1.0)
                
                # 处理任务
                self._process_audio_task(task)
                
                self.audio_task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"音频处理工作线程错误: {e}")
    
    def _process_audio_task(self, task: Dict):
        """
        处理音频任务
        
        Args:
            task: 音频任务
        """
        task_type = task.get('type')
        
        if task_type == 'recognize_file':
            # 文件识别任务
            result = self.asr.recognize_from_file(task['file_path'])
            if task.get('callback'):
                task['callback'](result)
        
        elif task_type == 'synthesize_to_file':
            # 文件合成任务
            success = self.tts.save_to_file(task['text'], task['file_path'])
            if task.get('callback'):
                task['callback'](success)
    
    def recognize_audio_file(self, file_path: str, callback: Optional[Callable] = None):
        """
        异步识别音频文件
        
        Args:
            file_path: 音频文件路径
            callback: 完成回调函数
        """
        task = {
            'type': 'recognize_file',
            'file_path': file_path,
            'callback': callback
        }
        self.audio_task_queue.put(task)
    
    def synthesize_to_file(self, text: str, file_path: str, callback: Optional[Callable] = None):
        """
        异步合成语音到文件
        
        Args:
            text: 要合成的文本
            file_path: 输出文件路径
            callback: 完成回调函数
        """
        task = {
            'type': 'synthesize_to_file',
            'text': text,
            'file_path': file_path,
            'callback': callback
        }
        self.audio_task_queue.put(task)
    
    def set_wake_words(self, wake_words: List[str]):
        """
        设置唤醒词
        
        Args:
            wake_words: 唤醒词列表
        """
        self.wake_words = wake_words
        self.logger.info(f"唤醒词已设置: {wake_words}")
    
    def enable_wake_word(self, enabled: bool = True):
        """
        启用/禁用唤醒词检测
        
        Args:
            enabled: 是否启用
        """
        self.wake_word_enabled = enabled
        status = "启用" if enabled else "禁用"
        self.logger.info(f"唤醒词检测已{status}")
    
    def is_speaking(self) -> bool:
        """
        检查是否正在播放语音
        
        Returns:
            是否正在播放
        """
        return self.tts.is_busy()
    
    def is_conversation_active(self) -> bool:
        """
        检查对话是否激活
        
        Returns:
            对话是否激活
        """
        return self.conversation_active
    
    # 回调函数管理方法
    def add_speech_recognized_callback(self, callback: Callable[[Dict], None]):
        """添加语音识别回调"""
        self.speech_recognized_callbacks.append(callback)
    
    def add_wake_word_detected_callback(self, callback: Callable[[str], None]):
        """添加唤醒词检测回调"""
        self.wake_word_detected_callbacks.append(callback)
    
    def add_conversation_started_callback(self, callback: Callable[[], None]):
        """添加对话开始回调"""
        self.conversation_started_callbacks.append(callback)
    
    def add_conversation_ended_callback(self, callback: Callable[[], None]):
        """添加对话结束回调"""
        self.conversation_ended_callbacks.append(callback)
    
    def get_audio_status(self) -> Dict:
        """
        获取音频系统状态
        
        Returns:
            状态信息字典
        """
        return {
            'listening': self.asr.is_listening,
            'speaking': self.is_speaking(),
            'conversation_active': self.conversation_active,
            'wake_word_enabled': self.wake_word_enabled,
            'processing_tasks': self.audio_task_queue.qsize()
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start_listening()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_listening()