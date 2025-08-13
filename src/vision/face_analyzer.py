"""
人脸分析模块
提供人脸检测、表情识别、专注度分析等功能
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

class FaceAnalyzer:
    def __init__(self):
        """
        初始化人脸分析器
        """
        self.logger = logging.getLogger(__name__)
        
        try:
            # 加载OpenCV人脸检测器
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            
            # 情绪状态映射
            self.emotion_labels = {
                0: 'angry',     # 愤怒
                1: 'disgust',   # 厌恶
                2: 'fear',      # 恐惧
                3: 'happy',     # 高兴
                4: 'sad',       # 悲伤
                5: 'surprise',  # 惊讶
                6: 'neutral'    # 中性
            }
            
            self.logger.info("人脸分析器初始化成功")
            
        except Exception as e:
            self.logger.error(f"人脸分析器初始化失败: {e}")
            raise
    
    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        """
        检测图像中的人脸
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            人脸检测结果列表，每个结果包含：
            {
                'bbox': [x, y, w, h],   # 人脸边界框
                'center': [cx, cy],     # 人脸中心点
                'confidence': float,    # 置信度
                'landmarks': {...}      # 面部关键点（如果可用）
            }
        """
        try:
            # 转换为灰度图像
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 检测人脸
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            face_results = []
            for (x, y, w, h) in faces:
                # 计算中心点
                center_x = x + w // 2
                center_y = y + h // 2
                
                # 检测眼部（用于专注度分析）
                face_roi = gray[y:y+h, x:x+w]
                eyes = self.eye_cascade.detectMultiScale(face_roi)
                
                result = {
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'center': [int(center_x), int(center_y)],
                    'confidence': 0.8,  # OpenCV级联分类器没有直接置信度
                    'eyes_detected': len(eyes),
                    'face_roi': face_roi
                }
                face_results.append(result)
            
            self.logger.debug(f"检测到 {len(face_results)} 张人脸")
            return face_results
            
        except Exception as e:
            self.logger.error(f"人脸检测失败: {e}")
            return []
    
    def analyze_attention(self, image: np.ndarray) -> Dict:
        """
        分析学生专注度
        
        Args:
            image: 输入图像
            
        Returns:
            专注度分析结果：
            {
                'attention_score': float,      # 专注度评分 (0-1)
                'face_direction': str,         # 面部朝向
                'eye_status': str,            # 眼部状态
                'engagement_level': str       # 参与度等级
            }
        """
        faces = self.detect_faces(image)
        
        if not faces:
            return {
                'attention_score': 0.0,
                'face_direction': 'unknown',
                'eye_status': 'no_face_detected',
                'engagement_level': 'low'
            }
        
        # 分析主要人脸（假设最大的人脸为主要关注对象）
        main_face = max(faces, key=lambda f: f['bbox'][2] * f['bbox'][3])
        
        # 基于眼部检测评估专注度
        eyes_detected = main_face['eyes_detected']
        bbox = main_face['bbox']
        
        # 简单的专注度评分算法
        attention_score = 0.0
        eye_status = 'closed'
        face_direction = 'forward'
        
        if eyes_detected >= 2:
            attention_score = 0.8
            eye_status = 'open'
        elif eyes_detected == 1:
            attention_score = 0.5
            eye_status = 'partially_open'
        
        # 根据人脸位置判断朝向
        image_center_x = image.shape[1] // 2
        face_center_x = main_face['center'][0]
        
        if abs(face_center_x - image_center_x) > 50:
            if face_center_x < image_center_x:
                face_direction = 'left'
            else:
                face_direction = 'right'
            attention_score *= 0.7  # 不正视时降低专注度
        
        # 专注度等级
        if attention_score >= 0.7:
            engagement_level = 'high'
        elif attention_score >= 0.4:
            engagement_level = 'medium'
        else:
            engagement_level = 'low'
        
        return {
            'attention_score': attention_score,
            'face_direction': face_direction,
            'eye_status': eye_status,
            'engagement_level': engagement_level
        }
    
    def detect_emotion(self, image: np.ndarray) -> List[Dict]:
        """
        检测情绪表情（简化版本）
        
        Args:
            image: 输入图像
            
        Returns:
            情绪检测结果
        """
        faces = self.detect_faces(image)
        emotion_results = []
        
        for face in faces:
            # 这里使用简化的情绪检测算法
            # 在实际项目中，可以集成更专业的情绪识别模型
            
            bbox = face['bbox']
            face_roi = face['face_roi']
            
            # 基于面部特征的简单情绪推断
            emotion = self._simple_emotion_detection(face_roi)
            
            emotion_result = {
                'bbox': bbox,
                'emotion': emotion,
                'confidence': 0.6  # 简化版本的固定置信度
            }
            emotion_results.append(emotion_result)
        
        return emotion_results
    
    def _simple_emotion_detection(self, face_roi: np.ndarray) -> str:
        """
        简单的情绪检测算法
        
        Args:
            face_roi: 人脸区域图像
            
        Returns:
            情绪标签
        """
        # 计算面部区域的亮度和纹理特征
        mean_brightness = np.mean(face_roi)
        
        # 简化的情绪推断规则
        if mean_brightness > 120:
            return 'happy'
        elif mean_brightness < 80:
            return 'sad'
        else:
            return 'neutral'
    
    def track_learning_state(self, image: np.ndarray, previous_state: Optional[Dict] = None) -> Dict:
        """
        跟踪学习状态变化
        
        Args:
            image: 当前图像
            previous_state: 上一次的状态
            
        Returns:
            学习状态分析结果
        """
        attention_result = self.analyze_attention(image)
        emotion_results = self.detect_emotion(image)
        
        current_state = {
            'timestamp': cv2.getTickCount(),
            'attention': attention_result,
            'emotions': emotion_results,
            'face_count': len(emotion_results)
        }
        
        # 如果有历史状态，计算变化趋势
        if previous_state:
            attention_change = (attention_result['attention_score'] - 
                              previous_state['attention']['attention_score'])
            current_state['attention_trend'] = 'improving' if attention_change > 0.1 else 'declining' if attention_change < -0.1 else 'stable'
        else:
            current_state['attention_trend'] = 'unknown'
        
        return current_state
    
    def draw_face_analysis(self, image: np.ndarray, faces: List[Dict], 
                          attention_result: Dict = None) -> np.ndarray:
        """
        在图像上绘制人脸分析结果
        
        Args:
            image: 输入图像
            faces: 人脸检测结果
            attention_result: 专注度分析结果
            
        Returns:
            绘制了分析结果的图像
        """
        result_image = image.copy()
        
        for face in faces:
            x, y, w, h = face['bbox']
            
            # 绘制人脸框
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            # 显示眼部检测结果
            eyes_text = f"Eyes: {face['eyes_detected']}"
            cv2.putText(result_image, eyes_text, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        # 显示专注度信息
        if attention_result:
            attention_text = f"Attention: {attention_result['attention_score']:.2f}"
            engagement_text = f"Level: {attention_result['engagement_level']}"
            
            cv2.putText(result_image, attention_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(result_image, engagement_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return result_image