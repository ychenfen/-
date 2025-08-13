"""
语音识别模块
基于Whisper实现语音转文字功能
"""

import numpy as np
import whisper
import pyaudio
import wave
import threading
import queue
from typing import Optional, Dict, List, Callable
import logging
import tempfile
import os

class SpeechRecognizer:
    def __init__(self, model_name: str = "small", language: str = "zh"):
        """
        初始化语音识别器
        
        Args:
            model_name: Whisper模型名称 ("tiny", "base", "small", "medium", "large")
            language: 识别语言 ("zh", "en", "auto")
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.language = language if language != "auto" else None
        
        # 音频参数
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        self.format = pyaudio.paInt16
        
        # 状态管理
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.listen_thread = None
        self.pyaudio_instance = None
        
        # 回调函数
        self.recognition_callbacks = []
        
        try:
            # 加载Whisper模型
            self.model = whisper.load_model(model_name)
            self.logger.info(f"Whisper模型加载成功: {model_name}")
        except Exception as e:
            self.logger.error(f"Whisper模型加载失败: {e}")
            raise
    
    def recognize_from_file(self, audio_file: str) -> Dict:
        """
        从音频文件识别语音
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            识别结果：
            {
                'text': str,           # 识别的文本
                'language': str,       # 检测的语言
                'confidence': float,   # 置信度
                'segments': list       # 分段结果
            }
        """
        try:
            # 使用Whisper进行识别
            result = self.model.transcribe(
                audio_file,
                language=self.language,
                task="transcribe"
            )
            
            # 计算平均置信度
            avg_confidence = 0.0
            if result.get('segments'):
                confidences = [seg.get('avg_logprob', 0) for seg in result['segments']]
                avg_confidence = np.mean(confidences) if confidences else 0.0
            
            recognition_result = {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'confidence': float(avg_confidence),
                'segments': result.get('segments', [])
            }
            
            self.logger.debug(f"识别结果: {recognition_result['text']}")
            return recognition_result
            
        except Exception as e:
            self.logger.error(f"语音识别失败: {e}")
            return {
                'text': '',
                'language': 'unknown',
                'confidence': 0.0,
                'segments': []
            }
    
    def recognize_from_array(self, audio_data: np.ndarray) -> Dict:
        """
        从音频数组识别语音
        
        Args:
            audio_data: 音频数据数组
            
        Returns:
            识别结果
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # 保存音频数据到临时文件
            self._save_audio_array(audio_data, temp_filename)
            
            # 进行识别
            result = self.recognize_from_file(temp_filename)
            
            # 删除临时文件
            os.unlink(temp_filename)
            
            return result
            
        except Exception as e:
            self.logger.error(f"从音频数组识别失败: {e}")
            return {
                'text': '',
                'language': 'unknown', 
                'confidence': 0.0,
                'segments': []
            }
    
    def start_continuous_recognition(self) -> bool:
        """
        开始连续语音识别
        
        Returns:
            是否启动成功
        """
        if self.is_listening:
            self.logger.warning("连续识别已经在运行")
            return True
        
        try:
            # 初始化PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # 开启音频流
            self.stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_listening = True
            self.listen_thread = threading.Thread(target=self._continuous_listen_loop)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
            self.logger.info("连续语音识别开始")
            return True
            
        except Exception as e:
            self.logger.error(f"启动连续识别失败: {e}")
            return False
    
    def stop_continuous_recognition(self):
        """
        停止连续语音识别
        """
        self.is_listening = False
        
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        self.logger.info("连续语音识别停止")
    
    def _continuous_listen_loop(self):
        """
        连续监听循环
        """
        audio_buffer = []
        silence_counter = 0
        min_audio_length = int(self.sample_rate * 1.0)  # 最少1秒音频
        max_silence = int(self.sample_rate * 2.0 / self.chunk_size)  # 最多2秒静音
        
        while self.is_listening:
            try:
                # 读取音频数据
                audio_chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
                
                # 检测音频活动
                volume = np.sqrt(np.mean(audio_data**2))
                
                if volume > 500:  # 有音频活动
                    audio_buffer.extend(audio_data)
                    silence_counter = 0
                else:  # 静音
                    silence_counter += 1
                    if len(audio_buffer) > 0:
                        audio_buffer.extend(audio_data)
                
                # 当检测到足够长的静音或缓冲区过大时处理音频
                if ((silence_counter > max_silence and len(audio_buffer) > min_audio_length) or
                    len(audio_buffer) > self.sample_rate * 30):  # 最长30秒
                    
                    if len(audio_buffer) > min_audio_length:
                        # 识别音频
                        audio_array = np.array(audio_buffer, dtype=np.float32) / 32768.0
                        result = self.recognize_from_array(audio_array)
                        
                        # 调用回调函数
                        if result['text'] and result['confidence'] > -1.0:
                            for callback in self.recognition_callbacks:
                                try:
                                    callback(result)
                                except Exception as e:
                                    self.logger.error(f"识别回调函数执行失败: {e}")
                    
                    # 清空缓冲区
                    audio_buffer = []
                    silence_counter = 0
                    
            except Exception as e:
                self.logger.error(f"连续识别循环错误: {e}")
                break
    
    def _save_audio_array(self, audio_data: np.ndarray, filename: str):
        """
        保存音频数组到文件
        
        Args:
            audio_data: 音频数据
            filename: 文件名
        """
        # 确保数据类型正确
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
        
        # 写入WAV文件
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
    
    def add_recognition_callback(self, callback: Callable[[Dict], None]):
        """
        添加识别结果回调函数
        
        Args:
            callback: 回调函数，接收识别结果字典作为参数
        """
        self.recognition_callbacks.append(callback)
        self.logger.debug("添加识别回调函数")
    
    def remove_recognition_callback(self, callback: Callable[[Dict], None]):
        """
        移除识别结果回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.recognition_callbacks:
            self.recognition_callbacks.remove(callback)
            self.logger.debug("移除识别回调函数")
    
    def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """
        录制指定时长的音频
        
        Args:
            duration: 录制时长（秒）
            
        Returns:
            音频数据数组，失败则返回None
        """
        try:
            if not self.pyaudio_instance:
                self.pyaudio_instance = pyaudio.PyAudio()
            
            stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            frames = []
            frames_to_record = int(self.sample_rate * duration / self.chunk_size)
            
            self.logger.info(f"开始录音 {duration} 秒...")
            
            for _ in range(frames_to_record):
                data = stream.read(self.chunk_size)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # 转换为numpy数组
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
            audio_array = audio_data.astype(np.float32) / 32768.0
            
            self.logger.info("录音完成")
            return audio_array
            
        except Exception as e:
            self.logger.error(f"录音失败: {e}")
            return None
    
    def detect_language(self, audio_file: str) -> str:
        """
        检测音频语言
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            检测到的语言代码
        """
        try:
            # 使用Whisper检测语言
            audio = whisper.load_audio(audio_file)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            
            _, probs = self.model.detect_language(mel)
            detected_language = max(probs, key=probs.get)
            
            self.logger.debug(f"检测到语言: {detected_language}")
            return detected_language
            
        except Exception as e:
            self.logger.error(f"语言检测失败: {e}")
            return "unknown"
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_continuous_recognition()