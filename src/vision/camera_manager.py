"""
摄像头管理模块
统一管理摄像头输入和图像预处理
"""

import cv2
import numpy as np
from typing import Optional, Callable, Dict, Any
import threading
import time
import logging

class CameraManager:
    def __init__(self, camera_id: int = 0, resolution: tuple = (1280, 720)):
        """
        初始化摄像头管理器
        
        Args:
            camera_id: 摄像头设备ID
            resolution: 分辨率 (width, height)
        """
        self.logger = logging.getLogger(__name__)
        self.camera_id = camera_id
        self.resolution = resolution
        self.cap = None
        self.is_streaming = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None
        
        # 回调函数列表
        self.frame_callbacks = []
        
    def initialize_camera(self) -> bool:
        """
        初始化摄像头
        
        Returns:
            是否初始化成功
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                self.logger.error(f"无法打开摄像头 {self.camera_id}")
                return False
            
            # 设置分辨率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            # 设置帧率
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.logger.info(f"摄像头初始化成功，分辨率: {self.resolution}")
            return True
            
        except Exception as e:
            self.logger.error(f"摄像头初始化失败: {e}")
            return False
    
    def start_streaming(self) -> bool:
        """
        开始视频流捕获
        
        Returns:
            是否启动成功
        """
        if not self.cap or not self.cap.isOpened():
            if not self.initialize_camera():
                return False
        
        if self.is_streaming:
            self.logger.warning("视频流已经在运行")
            return True
        
        self.is_streaming = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        self.logger.info("视频流捕获开始")
        return True
    
    def stop_streaming(self):
        """
        停止视频流捕获
        """
        self.is_streaming = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.logger.info("视频流捕获停止")
    
    def _capture_loop(self):
        """
        视频捕获循环
        """
        while self.is_streaming:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.error("读取帧失败")
                    break
                
                # 预处理帧
                processed_frame = self._preprocess_frame(frame)
                
                # 更新当前帧
                with self.frame_lock:
                    self.current_frame = processed_frame
                
                # 调用回调函数
                for callback in self.frame_callbacks:
                    try:
                        callback(processed_frame.copy())
                    except Exception as e:
                        self.logger.error(f"回调函数执行失败: {e}")
                
                # 控制帧率
                time.sleep(0.033)  # 约30fps
                
            except Exception as e:
                self.logger.error(f"视频捕获错误: {e}")
                break
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        预处理帧
        
        Args:
            frame: 原始帧
            
        Returns:
            预处理后的帧
        """
        # 镜像翻转
        frame = cv2.flip(frame, 1)
        
        # 色彩空间转换（如果需要）
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        获取当前帧
        
        Returns:
            当前帧图像，如果没有则返回None
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def capture_single_frame(self) -> Optional[np.ndarray]:
        """
        捕获单帧图像
        
        Returns:
            捕获的图像，失败则返回None
        """
        if not self.cap or not self.cap.isOpened():
            if not self.initialize_camera():
                return None
        
        try:
            ret, frame = self.cap.read()
            if ret:
                return self._preprocess_frame(frame)
            else:
                self.logger.error("单帧捕获失败")
                return None
        except Exception as e:
            self.logger.error(f"单帧捕获错误: {e}")
            return None
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """
        添加帧处理回调函数
        
        Args:
            callback: 回调函数，接收帧图像作为参数
        """
        self.frame_callbacks.append(callback)
        self.logger.debug("添加帧回调函数")
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """
        移除帧处理回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
            self.logger.debug("移除帧回调函数")
    
    def set_camera_property(self, property_id: int, value: float) -> bool:
        """
        设置摄像头属性
        
        Args:
            property_id: OpenCV属性ID
            value: 属性值
            
        Returns:
            是否设置成功
        """
        if self.cap and self.cap.isOpened():
            return self.cap.set(property_id, value)
        return False
    
    def get_camera_property(self, property_id: int) -> float:
        """
        获取摄像头属性
        
        Args:
            property_id: OpenCV属性ID
            
        Returns:
            属性值
        """
        if self.cap and self.cap.isOpened():
            return self.cap.get(property_id)
        return -1
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        获取摄像头信息
        
        Returns:
            摄像头信息字典
        """
        if not self.cap or not self.cap.isOpened():
            return {}
        
        info = {
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.cap.get(cv2.CAP_PROP_FPS),
            'brightness': self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
            'contrast': self.cap.get(cv2.CAP_PROP_CONTRAST),
            'saturation': self.cap.get(cv2.CAP_PROP_SATURATION),
            'hue': self.cap.get(cv2.CAP_PROP_HUE)
        }
        
        return info
    
    def save_frame(self, filename: str, frame: Optional[np.ndarray] = None) -> bool:
        """
        保存帧到文件
        
        Args:
            filename: 文件名
            frame: 要保存的帧，如果为None则保存当前帧
            
        Returns:
            是否保存成功
        """
        try:
            if frame is None:
                frame = self.get_current_frame()
            
            if frame is not None:
                cv2.imwrite(filename, frame)
                self.logger.info(f"帧已保存到: {filename}")
                return True
            else:
                self.logger.error("没有可保存的帧")
                return False
                
        except Exception as e:
            self.logger.error(f"保存帧失败: {e}")
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start_streaming()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_streaming()