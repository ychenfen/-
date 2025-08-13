"""
OCR文字识别模块
基于PaddleOCR实现中英文文字识别
"""

import cv2
import numpy as np
from paddleocr import PaddleOCR
from typing import List, Dict, Tuple, Optional
import logging
import re

class OCRProcessor:
    def __init__(self, use_angle_cls: bool = True, lang: str = 'ch'):
        """
        初始化OCR处理器
        
        Args:
            use_angle_cls: 是否使用文本方向分类器
            lang: 语言类型 ('ch', 'en', 'japanese', 'korean')
        """
        self.logger = logging.getLogger(__name__)
        
        try:
            self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
            self.logger.info(f"PaddleOCR初始化成功，语言: {lang}")
        except Exception as e:
            self.logger.error(f"PaddleOCR初始化失败: {e}")
            raise
            
    def recognize_text(self, image: np.ndarray, confidence_threshold: float = 0.5) -> List[Dict]:
        """
        识别图像中的文字
        
        Args:
            image: 输入图像 (BGR格式)
            confidence_threshold: 置信度阈值
            
        Returns:
            识别结果列表，每个结果包含：
            {
                'text': str,           # 识别的文字
                'confidence': float,   # 置信度
                'bbox': [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], # 四边形坐标
                'center': [cx, cy]     # 中心点坐标
            }
        """
        try:
            # 使用PaddleOCR进行文字识别
            results = self.ocr.ocr(image, cls=True)
            
            text_results = []
            if results and results[0]:
                for line in results[0]:
                    if line:
                        bbox = line[0]
                        text_info = line[1]
                        text = text_info[0]
                        confidence = text_info[1]
                        
                        if confidence >= confidence_threshold:
                            # 计算中心点
                            bbox_array = np.array(bbox)
                            center_x = np.mean(bbox_array[:, 0])
                            center_y = np.mean(bbox_array[:, 1])
                            
                            result = {
                                'text': text.strip(),
                                'confidence': float(confidence),
                                'bbox': bbox,
                                'center': [int(center_x), int(center_y)]
                            }
                            text_results.append(result)
            
            self.logger.debug(f"识别到 {len(text_results)} 段文字")
            return text_results
            
        except Exception as e:
            self.logger.error(f"OCR识别失败: {e}")
            return []
    
    def recognize_mathematical_expressions(self, image: np.ndarray) -> List[Dict]:
        """
        识别数学表达式
        
        Args:
            image: 输入图像
            
        Returns:
            数学表达式识别结果
        """
        text_results = self.recognize_text(image)
        math_expressions = []
        
        # 数学表达式的正则模式
        math_patterns = [
            r'\d+\s*[\+\-\×\÷\*\/]\s*\d+',  # 基本算术
            r'\d+\s*[=]\s*\d+',             # 等式
            r'[xy]\s*[\+\-]\s*\d+',         # 代数表达式
            r'\d+\^\d+',                    # 幂运算
            r'√\d+',                        # 开方
            r'\(\d+[\+\-]\d+\)',            # 括号表达式
        ]
        
        for result in text_results:
            text = result['text']
            for pattern in math_patterns:
                if re.search(pattern, text):
                    result['type'] = 'mathematical'
                    math_expressions.append(result)
                    break
        
        return math_expressions
    
    def extract_keywords(self, image: np.ndarray, keyword_list: List[str]) -> List[Dict]:
        """
        提取指定关键词
        
        Args:
            image: 输入图像
            keyword_list: 关键词列表
            
        Returns:
            包含关键词的文本结果
        """
        text_results = self.recognize_text(image)
        keyword_results = []
        
        for result in text_results:
            text = result['text'].lower()
            for keyword in keyword_list:
                if keyword.lower() in text:
                    result['keyword'] = keyword
                    keyword_results.append(result)
                    break
        
        return keyword_results
    
    def recognize_handwriting(self, image: np.ndarray) -> List[Dict]:
        """
        识别手写文字
        
        Args:
            image: 输入图像
            
        Returns:
            手写文字识别结果
        """
        # 对手写文字进行预处理
        processed_image = self._preprocess_handwriting(image)
        return self.recognize_text(processed_image, confidence_threshold=0.3)
    
    def _preprocess_handwriting(self, image: np.ndarray) -> np.ndarray:
        """
        手写文字预处理
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的图像
        """
        # 转灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # 自适应阈值二值化
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # 形态学操作
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def draw_text_results(self, image: np.ndarray, text_results: List[Dict]) -> np.ndarray:
        """
        在图像上绘制文字识别结果
        
        Args:
            image: 输入图像
            text_results: 文字识别结果列表
            
        Returns:
            绘制了文字框的图像
        """
        result_image = image.copy()
        
        for result in text_results:
            bbox = result['bbox']
            text = result['text']
            confidence = result['confidence']
            
            # 绘制文字边界框
            points = np.array(bbox, dtype=np.int32)
            cv2.polylines(result_image, [points], True, (0, 255, 0), 2)
            
            # 在左上角显示文字内容
            label = f"{text} ({confidence:.2f})"
            cv2.putText(result_image, label, (points[0][0], points[0][1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return result_image
    
    def get_text_by_region(self, image: np.ndarray, region: Tuple[int, int, int, int]) -> List[Dict]:
        """
        识别指定区域内的文字
        
        Args:
            image: 输入图像
            region: 区域坐标 (x, y, width, height)
            
        Returns:
            区域内的文字识别结果
        """
        x, y, w, h = region
        roi = image[y:y+h, x:x+w]
        return self.recognize_text(roi)