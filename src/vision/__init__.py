"""
视觉模块
提供目标检测、OCR识别、人脸检测等计算机视觉功能
"""

from .detector import ObjectDetector
from .ocr import OCRProcessor  
from .face_analyzer import FaceAnalyzer

__all__ = ['ObjectDetector', 'OCRProcessor', 'FaceAnalyzer']