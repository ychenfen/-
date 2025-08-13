"""
语音合成模块
基于pyttsx3实现文字转语音功能
"""

import pyttsx3
import threading
import queue
import time
from typing import Optional, Dict, List, Callable
import logging
import tempfile
import os

class TextToSpeech:
    def __init__(self, voice_rate: int = 200, voice_volume: float = 0.9):
        """
        初始化语音合成器
        
        Args:
            voice_rate: 语音速度 (words per minute)
            voice_volume: 音量 (0.0-1.0)
        """
        self.logger = logging.getLogger(__name__)
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume
        
        # 语音队列和线程管理
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.speech_thread = None
        self.stop_flag = threading.Event()
        
        # 回调函数
        self.speech_callbacks = []
        
        try:
            # 初始化TTS引擎
            self.engine = pyttsx3.init()
            self._configure_engine()
            self.logger.info("TTS引擎初始化成功")
        except Exception as e:
            self.logger.error(f"TTS引擎初始化失败: {e}")
            raise
    
    def _configure_engine(self):
        """
        配置TTS引擎参数
        """
        try:
            # 设置语音速度
            self.engine.setProperty('rate', self.voice_rate)
            
            # 设置音量
            self.engine.setProperty('volume', self.voice_volume)
            
            # 获取可用语音
            voices = self.engine.getProperty('voices')
            
            # 优先选择中文语音
            chinese_voice = None
            for voice in voices:
                if 'zh' in voice.id.lower() or 'chinese' in voice.name.lower():
                    chinese_voice = voice
                    break
            
            if chinese_voice:
                self.engine.setProperty('voice', chinese_voice.id)
                self.logger.info(f"使用中文语音: {chinese_voice.name}")
            else:
                # 使用第一个可用语音
                if voices:
                    self.engine.setProperty('voice', voices[0].id)
                    self.logger.info(f"使用默认语音: {voices[0].name}")
            
        except Exception as e:
            self.logger.error(f"TTS引擎配置失败: {e}")
    
    def speak(self, text: str, blocking: bool = False) -> bool:
        """
        语音合成
        
        Args:
            text: 要合成的文本
            blocking: 是否阻塞等待完成
            
        Returns:
            是否成功添加到合成队列
        """
        if not text.strip():
            return False
        
        try:
            speech_item = {
                'text': text,
                'timestamp': time.time(),
                'blocking': blocking
            }
            
            self.speech_queue.put(speech_item)
            
            # 启动语音合成线程
            if not self.is_speaking:
                self._start_speech_thread()
            
            if blocking:
                # 等待当前语音完成
                while not self.speech_queue.empty() or self.is_speaking:
                    time.sleep(0.1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"语音合成失败: {e}")
            return False
    
    def speak_with_emotion(self, text: str, emotion: str = "neutral", blocking: bool = False) -> bool:
        """
        带情感的语音合成
        
        Args:
            text: 要合成的文本
            emotion: 情感类型 ("happy", "sad", "excited", "calm", "neutral")
            blocking: 是否阻塞等待完成
            
        Returns:
            是否成功
        """
        # 根据情感调整语音参数
        original_rate = self.engine.getProperty('rate')
        original_volume = self.engine.getProperty('volume')
        
        try:
            if emotion == "happy" or emotion == "excited":
                self.engine.setProperty('rate', original_rate + 50)
                self.engine.setProperty('volume', min(1.0, original_volume + 0.1))
            elif emotion == "sad":
                self.engine.setProperty('rate', original_rate - 30)
                self.engine.setProperty('volume', max(0.1, original_volume - 0.2))
            elif emotion == "calm":
                self.engine.setProperty('rate', original_rate - 20)
                self.engine.setProperty('volume', original_volume)
            
            # 合成语音
            result = self.speak(text, blocking)
            
            # 恢复原始参数
            self.engine.setProperty('rate', original_rate)
            self.engine.setProperty('volume', original_volume)
            
            return result
            
        except Exception as e:
            self.logger.error(f"情感语音合成失败: {e}")
            # 恢复原始参数
            self.engine.setProperty('rate', original_rate)
            self.engine.setProperty('volume', original_volume)
            return False
    
    def speak_educational_content(self, content: str, content_type: str = "explanation") -> bool:
        """
        教育内容语音合成
        
        Args:
            content: 教育内容
            content_type: 内容类型 ("explanation", "question", "answer", "encouragement")
            
        Returns:
            是否成功
        """
        # 根据内容类型添加前缀和调整语调
        prefix = ""
        emotion = "neutral"
        
        if content_type == "question":
            prefix = "让我来问你一个问题："
            emotion = "excited"
        elif content_type == "answer":
            prefix = "答案是："
            emotion = "calm"
        elif content_type == "encouragement":
            prefix = "很好！"
            emotion = "happy"
        elif content_type == "explanation":
            prefix = "让我来解释一下："
            emotion = "calm"
        
        full_text = prefix + content
        return self.speak_with_emotion(full_text, emotion, blocking=False)
    
    def _start_speech_thread(self):
        """
        启动语音合成线程
        """
        if self.speech_thread and self.speech_thread.is_alive():
            return
        
        self.is_speaking = True
        self.stop_flag.clear()
        self.speech_thread = threading.Thread(target=self._speech_worker)
        self.speech_thread.daemon = True
        self.speech_thread.start()
    
    def _speech_worker(self):
        """
        语音合成工作线程
        """
        while not self.stop_flag.is_set():
            try:
                # 获取语音任务
                speech_item = self.speech_queue.get(timeout=1.0)
                
                # 执行语音合成
                self._synthesize_speech(speech_item['text'])
                
                # 调用回调函数
                for callback in self.speech_callbacks:
                    try:
                        callback(speech_item)
                    except Exception as e:
                        self.logger.error(f"语音回调函数执行失败: {e}")
                
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"语音合成工作线程错误: {e}")
        
        self.is_speaking = False
    
    def _synthesize_speech(self, text: str):
        """
        执行语音合成
        
        Args:
            text: 要合成的文本
        """
        try:
            self.logger.debug(f"开始合成语音: {text[:50]}...")
            self.engine.say(text)
            self.engine.runAndWait()
            self.logger.debug("语音合成完成")
        except Exception as e:
            self.logger.error(f"语音合成执行失败: {e}")
    
    def stop_speaking(self):
        """
        停止当前语音合成
        """
        try:
            self.engine.stop()
            self.stop_flag.set()
            
            # 清空队列
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except queue.Empty:
                    break
            
            self.logger.info("语音合成已停止")
        except Exception as e:
            self.logger.error(f"停止语音合成失败: {e}")
    
    def save_to_file(self, text: str, filename: str) -> bool:
        """
        将语音保存到文件
        
        Args:
            text: 要合成的文本
            filename: 输出文件名
            
        Returns:
            是否保存成功
        """
        try:
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
            self.logger.info(f"语音已保存到: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"保存语音文件失败: {e}")
            return False
    
    def set_voice_properties(self, rate: Optional[int] = None, 
                           volume: Optional[float] = None,
                           voice_id: Optional[str] = None) -> bool:
        """
        设置语音属性
        
        Args:
            rate: 语音速度
            volume: 音量
            voice_id: 语音ID
            
        Returns:
            是否设置成功
        """
        try:
            if rate is not None:
                self.engine.setProperty('rate', rate)
                self.voice_rate = rate
            
            if volume is not None:
                self.engine.setProperty('volume', volume)
                self.voice_volume = volume
            
            if voice_id is not None:
                self.engine.setProperty('voice', voice_id)
            
            self.logger.info("语音属性设置成功")
            return True
            
        except Exception as e:
            self.logger.error(f"设置语音属性失败: {e}")
            return False
    
    def get_available_voices(self) -> List[Dict]:
        """
        获取可用语音列表
        
        Returns:
            语音信息列表
        """
        try:
            voices = self.engine.getProperty('voices')
            voice_list = []
            
            for voice in voices:
                voice_info = {
                    'id': voice.id,
                    'name': voice.name,
                    'age': getattr(voice, 'age', None),
                    'gender': getattr(voice, 'gender', None),
                    'languages': getattr(voice, 'languages', [])
                }
                voice_list.append(voice_info)
            
            return voice_list
            
        except Exception as e:
            self.logger.error(f"获取语音列表失败: {e}")
            return []
    
    def add_speech_callback(self, callback: Callable[[Dict], None]):
        """
        添加语音合成回调函数
        
        Args:
            callback: 回调函数，接收语音任务字典作为参数
        """
        self.speech_callbacks.append(callback)
        self.logger.debug("添加语音回调函数")
    
    def remove_speech_callback(self, callback: Callable[[Dict], None]):
        """
        移除语音合成回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.speech_callbacks:
            self.speech_callbacks.remove(callback)
            self.logger.debug("移除语音回调函数")
    
    def is_busy(self) -> bool:
        """
        检查是否正在合成语音
        
        Returns:
            是否正忙
        """
        return self.is_speaking or not self.speech_queue.empty()
    
    def wait_until_done(self, timeout: Optional[float] = None):
        """
        等待语音合成完成
        
        Args:
            timeout: 超时时间（秒），None表示无限等待
        """
        start_time = time.time()
        
        while self.is_busy():
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning("等待语音合成完成超时")
                break
            time.sleep(0.1)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_speaking()