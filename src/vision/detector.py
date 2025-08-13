"""
目标检测模块
基于YOLOv8实现物体检测和识别
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Tuple, Optional
import logging

class ObjectDetector:
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.5):
        """
        初始化物体检测器
        
        Args:
            model_path: YOLO模型路径
            confidence_threshold: 置信度阈值
        """
        self.logger = logging.getLogger(__name__)
        self.confidence_threshold = confidence_threshold
        
        try:
            self.model = YOLO(model_path)
            self.logger.info(f"YOLO模型加载成功: {model_path}")
        except Exception as e:
            self.logger.error(f"YOLO模型加载失败: {e}")
            raise
    
    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        检测图像中的物体
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            检测结果列表，每个结果包含：
            {
                'class_name': str,      # 类别名称
                'confidence': float,    # 置信度
                'bbox': [x1, y1, x2, y2],  # 边界框坐标
                'center': [cx, cy]      # 中心点坐标
            }
        """
        try:
            # 使用YOLO进行检测
            results = self.model(image, conf=self.confidence_threshold)
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names[class_id]
                        
                        # 计算中心点
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        
                        detection = {
                            'class_name': class_name,
                            'confidence': float(confidence),
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'center': [int(center_x), int(center_y)]
                        }
                        detections.append(detection)
            
            self.logger.debug(f"检测到 {len(detections)} 个物体")
            return detections
            
        except Exception as e:
            self.logger.error(f"物体检测失败: {e}")
            return []
    
    def detect_educational_objects(self, image: np.ndarray) -> Dict[str, List[Dict]]:
        """
        检测教育相关物体
        
        Args:
            image: 输入图像
            
        Returns:
            分类的检测结果：
            {
                'books': [...],      # 书籍
                'writing_tools': [...], # 文具
                'electronic': [...], # 电子设备
                'others': [...]      # 其他物体
            }
        """
        detections = self.detect(image)
        
        # 教育物品分类映射
        educational_categories = {
            'books': ['book'],
            'writing_tools': ['pencil', 'pen'],
            'electronic': ['laptop', 'tablet', 'phone', 'computer'],
            'others': []
        }
        
        categorized_results = {
            'books': [],
            'writing_tools': [],
            'electronic': [],
            'others': []
        }
        
        for detection in detections:
            class_name = detection['class_name']
            categorized = False
            
            for category, class_list in educational_categories.items():
                if class_name in class_list:
                    categorized_results[category].append(detection)
                    categorized = True
                    break
            
            if not categorized:
                categorized_results['others'].append(detection)
        
        return categorized_results
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        在图像上绘制检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果列表
            
        Returns:
            绘制了检测框的图像
        """
        result_image = image.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            class_name = detection['class_name'] 
            confidence = detection['confidence']
            
            # 绘制边界框
            cv2.rectangle(result_image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_image, (bbox[0], bbox[1] - label_size[1] - 10), 
                         (bbox[0] + label_size[0], bbox[1]), (0, 255, 0), -1)
            cv2.putText(result_image, label, (bbox[0], bbox[1] - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return result_image
    
    def get_nearest_object(self, detections: List[Dict], target_point: Tuple[int, int]) -> Optional[Dict]:
        """
        获取最接近目标点的物体
        
        Args:
            detections: 检测结果列表
            target_point: 目标点坐标 (x, y)
            
        Returns:
            最近的检测结果，如果没有则返回None
        """
        if not detections:
            return None
        
        min_distance = float('inf')
        nearest_detection = None
        
        for detection in detections:
            center = detection['center']
            distance = np.sqrt((center[0] - target_point[0])**2 + (center[1] - target_point[1])**2)
            
            if distance < min_distance:
                min_distance = distance
                nearest_detection = detection
        
        return nearest_detection