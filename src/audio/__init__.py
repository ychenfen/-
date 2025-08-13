"""
语音模块
提供语音识别(ASR)、语音合成(TTS)和音频处理功能
"""

from .asr import SpeechRecognizer
from .tts import TextToSpeech
from .audio_manager import AudioManager

__all__ = ['SpeechRecognizer', 'TextToSpeech', 'AudioManager']