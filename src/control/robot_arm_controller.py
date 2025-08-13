"""
机械臂控制器
基于myCobot 280 RISC-V实现精确的机械臂控制
"""

import time
import threading
import queue
from typing import List, Tuple, Dict, Any, Optional, Callable
from enum import Enum
import logging
import numpy as np

# 模拟myCobot库（实际项目中需要安装真实的库）
try:
    from pymycobot.mycobot280 import MyCobot280
except ImportError:
    # 模拟类用于开发测试
    class MyCobot280:
        def __init__(self, port, baudrate=115200):
            self.port = port
            self.angles = [0, 0, 0, 0, 0, 0]
            self.coords = [200, 0, 200, 0, 0, 0]
        
        def send_angles(self, angles, speed): pass
        def send_coords(self, coords, speed): pass  
        def get_angles(self): return self.angles
        def get_coords(self): return self.coords
        def set_gripper_state(self, state, speed): pass
        def is_moving(self): return False

class ArmState(Enum):
    """机械臂状态枚举"""
    IDLE = "idle"
    MOVING = "moving"
    POINTING = "pointing"
    DEMONSTRATING = "demonstrating"
    GESTURING = "gesturing"
    ERROR = "error"

class RobotArmController:
    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        """
        初始化机械臂控制器
        
        Args:
            port: 串口端口
            baudrate: 波特率
        """
        self.logger = logging.getLogger(__name__)
        self.port = port
        self.baudrate = baudrate
        
        # 机械臂状态
        self.current_state = ArmState.IDLE
        self.is_connected = False
        
        # 动作队列和执行线程
        self.action_queue = queue.Queue()
        self.action_thread = None
        self.is_executing = False
        
        # 回调函数
        self.action_callbacks = []
        self.state_callbacks = []
        
        # 安全限制
        self.joint_limits = {
            'J1': (-165, 165),  # 度
            'J2': (-165, 165),
            'J3': (-165, 165),
            'J4': (-165, 165),
            'J5': (-165, 165),
            'J6': (-175, 175)
        }
        
        self.workspace_limits = {
            'x': (-300, 300),  # mm
            'y': (-300, 300),
            'z': (0, 400)
        }
        
        # 预定义姿态
        self.predefined_poses = {
            'home': [0, 0, 0, 0, 0, 0],
            'rest': [0, -45, -90, 0, 45, 0],
            'point_forward': [0, -30, -60, 0, 90, 0],
            'point_left': [45, -30, -60, 0, 90, 0],
            'point_right': [-45, -30, -60, 0, 90, 0],
            'wave_start': [0, -45, -45, 0, 0, 0],
            'demonstrate_pick': [0, -60, -90, 0, 60, 0]
        }
        
        try:
            self._initialize_arm()
            self.logger.info("机械臂控制器初始化成功")
        except Exception as e:
            self.logger.error(f"机械臂控制器初始化失败: {e}")
            raise
    
    def _initialize_arm(self):
        """
        初始化机械臂连接
        """
        try:
            self.arm = MyCobot280(self.port, self.baudrate)
            self.is_connected = True
            
            # 启动动作执行线程
            self._start_action_thread()
            
            # 移动到初始位置
            self.move_to_pose('home', speed=50)
            
            self.logger.info(f"机械臂连接成功: {self.port}")
            
        except Exception as e:
            self.logger.error(f"机械臂连接失败: {e}")
            self.is_connected = False
            raise
    
    def _start_action_thread(self):
        """
        启动动作执行线程
        """
        if self.action_thread and self.action_thread.is_alive():
            return
        
        self.is_executing = True
        self.action_thread = threading.Thread(target=self._action_executor)
        self.action_thread.daemon = True
        self.action_thread.start()
    
    def _stop_action_thread(self):
        """
        停止动作执行线程
        """
        self.is_executing = False
        if self.action_thread:
            self.action_thread.join(timeout=2.0)
    
    def _action_executor(self):
        """
        动作执行线程
        """
        while self.is_executing:
            try:
                # 获取动作任务
                action = self.action_queue.get(timeout=1.0)
                
                # 执行动作
                self._execute_action(action)
                
                self.action_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"动作执行错误: {e}")
                self._set_state(ArmState.ERROR)
    
    def _execute_action(self, action: Dict[str, Any]):
        """
        执行具体动作
        
        Args:
            action: 动作参数字典
        """
        action_type = action.get('type')
        params = action.get('params', {})
        
        try:
            self._set_state(ArmState.MOVING)
            
            if action_type == 'move_angles':
                self._move_angles(params['angles'], params.get('speed', 50))
            
            elif action_type == 'move_coords':
                self._move_coords(params['coords'], params.get('speed', 50))
            
            elif action_type == 'point_to':
                self._point_to_position(params['target'], params.get('speed', 30))
            
            elif action_type == 'gesture':
                self._perform_gesture(params['gesture_name'], params.get('repeat', 1))
            
            elif action_type == 'demonstrate':
                self._demonstrate_action(params['demo_type'], params.get('params', {}))
            
            elif action_type == 'gripper':
                self._control_gripper(params['state'], params.get('speed', 50))
            
            else:
                self.logger.warning(f"未知动作类型: {action_type}")
                return
            
            # 等待动作完成
            self._wait_for_completion()
            
            # 调用回调函数
            for callback in self.action_callbacks:
                try:
                    callback(action)
                except Exception as e:
                    self.logger.error(f"动作回调执行失败: {e}")
            
            self._set_state(ArmState.IDLE)
            
        except Exception as e:
            self.logger.error(f"执行动作失败: {e}")
            self._set_state(ArmState.ERROR)
    
    def move_to_pose(self, pose_name: str, speed: int = 50) -> bool:
        """
        移动到预定义姿态
        
        Args:
            pose_name: 姿态名称
            speed: 移动速度 (1-100)
            
        Returns:
            是否成功添加到执行队列
        """
        if pose_name not in self.predefined_poses:
            self.logger.error(f"未知姿态: {pose_name}")
            return False
        
        angles = self.predefined_poses[pose_name]
        
        action = {
            'type': 'move_angles',
            'params': {
                'angles': angles,
                'speed': speed
            },
            'description': f'移动到姿态: {pose_name}'
        }
        
        self.action_queue.put(action)
        self.logger.debug(f"添加动作: 移动到 {pose_name}")
        return True
    
    def point_to_position(self, target_position: Tuple[float, float, float], 
                         speed: int = 30) -> bool:
        """
        指向指定位置
        
        Args:
            target_position: 目标位置 (x, y, z)
            speed: 移动速度
            
        Returns:
            是否成功
        """
        if not self._validate_position(target_position):
            self.logger.error(f"目标位置超出工作空间: {target_position}")
            return False
        
        action = {
            'type': 'point_to',
            'params': {
                'target': target_position,
                'speed': speed
            },
            'description': f'指向位置: {target_position}'
        }
        
        self.action_queue.put(action)
        self.logger.debug(f"添加动作: 指向 {target_position}")
        return True
    
    def perform_educational_gesture(self, gesture_type: str, params: Dict = None) -> bool:
        """
        执行教育手势
        
        Args:
            gesture_type: 手势类型
            params: 手势参数
            
        Returns:
            是否成功
        """
        educational_gestures = {
            'greeting': self._greeting_gesture,
            'pointing': self._pointing_gesture,
            'encouragement': self._encouragement_gesture,
            'explanation': self._explanation_gesture,
            'question': self._question_gesture,
            'thinking': self._thinking_gesture
        }
        
        if gesture_type not in educational_gestures:
            self.logger.error(f"未知教育手势: {gesture_type}")
            return False
        
        action = {
            'type': 'gesture',
            'params': {
                'gesture_name': gesture_type,
                'params': params or {}
            },
            'description': f'执行教育手势: {gesture_type}'
        }
        
        self.action_queue.put(action)
        self.logger.debug(f"添加动作: 教育手势 {gesture_type}")
        return True
    
    def demonstrate_concept(self, concept_type: str, params: Dict = None) -> bool:
        """
        演示教学概念
        
        Args:
            concept_type: 概念类型
            params: 演示参数
            
        Returns:
            是否成功
        """
        demonstration_types = {
            'counting': self._demonstrate_counting,
            'shapes': self._demonstrate_shapes,
            'directions': self._demonstrate_directions,
            'size_comparison': self._demonstrate_sizes,
            'writing': self._demonstrate_writing
        }
        
        if concept_type not in demonstration_types:
            self.logger.error(f"未知演示类型: {concept_type}")
            return False
        
        action = {
            'type': 'demonstrate',
            'params': {
                'demo_type': concept_type,
                'params': params or {}
            },
            'description': f'演示概念: {concept_type}'
        }
        
        self.action_queue.put(action)
        self.logger.debug(f"添加动作: 演示 {concept_type}")
        return True
    
    def _move_angles(self, angles: List[float], speed: int):
        """
        移动关节角度
        """
        if not self._validate_angles(angles):
            raise ValueError("关节角度超出限制")
        
        self.arm.send_angles(angles, speed)
        self.logger.debug(f"发送关节角度: {angles}")
    
    def _move_coords(self, coords: List[float], speed: int):
        """
        移动到坐标位置
        """
        if not self._validate_coordinates(coords):
            raise ValueError("坐标位置超出限制")
        
        self.arm.send_coords(coords, speed)
        self.logger.debug(f"发送坐标: {coords}")
    
    def _point_to_position(self, target: Tuple[float, float, float], speed: int):
        """
        指向特定位置
        """
        # 计算指向目标的关节角度
        current_coords = self.arm.get_coords()
        
        # 简化的指向计算（实际应使用逆运动学）
        pointing_coords = [target[0], target[1], target[2], 0, 90, 0]
        
        self._move_coords(pointing_coords, speed)
        self._set_state(ArmState.POINTING)
    
    def _perform_gesture(self, gesture_name: str, repeat: int = 1):
        """
        执行手势动作
        """
        gesture_functions = {
            'greeting': self._greeting_gesture,
            'pointing': self._pointing_gesture,
            'encouragement': self._encouragement_gesture,
            'explanation': self._explanation_gesture,
            'question': self._question_gesture,
            'thinking': self._thinking_gesture
        }
        
        gesture_func = gesture_functions.get(gesture_name)
        if gesture_func:
            for _ in range(repeat):
                gesture_func()
                if repeat > 1:
                    time.sleep(0.5)
        
        self._set_state(ArmState.GESTURING)
    
    def _demonstrate_action(self, demo_type: str, params: Dict):
        """
        执行演示动作
        """
        demo_functions = {
            'counting': self._demonstrate_counting,
            'shapes': self._demonstrate_shapes,
            'directions': self._demonstrate_directions,
            'size_comparison': self._demonstrate_sizes,
            'writing': self._demonstrate_writing
        }
        
        demo_func = demo_functions.get(demo_type)
        if demo_func:
            demo_func(**params)
        
        self._set_state(ArmState.DEMONSTRATING)
    
    def _greeting_gesture(self):
        """问候手势"""
        # 挥手动作
        poses = [
            [0, -45, -45, 0, 0, 0],     # 起始位置
            [0, -45, -45, 0, 0, 45],    # 向右
            [0, -45, -45, 0, 0, -45],   # 向左
            [0, -45, -45, 0, 0, 45],    # 向右
            [0, -45, -45, 0, 0, 0]      # 回到起始
        ]
        
        for pose in poses:
            self._move_angles(pose, 60)
            time.sleep(0.5)
    
    def _pointing_gesture(self):
        """指向手势"""
        # 指向前方
        self._move_angles([0, -30, -60, 0, 90, 0], 40)
        time.sleep(1.0)
        self._move_angles([0, 0, 0, 0, 0, 0], 40)  # 回到初始位置
    
    def _encouragement_gesture(self):
        """鼓励手势（竖拇指）"""
        poses = [
            [0, -45, -90, 0, 45, 0],    # 准备位置
            [0, -30, -60, 0, 30, 90],   # 竖拇指
        ]
        
        for pose in poses:
            self._move_angles(pose, 50)
            time.sleep(0.8)
        
        # 回到初始位置
        self._move_angles([0, 0, 0, 0, 0, 0], 50)
    
    def _explanation_gesture(self):
        """解释手势（展开双臂般的动作）"""
        poses = [
            [0, -45, -45, 0, 0, 0],     # 中间位置
            [45, -45, -45, 0, 0, 0],    # 向左展开
            [-45, -45, -45, 0, 0, 0],   # 向右展开
            [0, -45, -45, 0, 0, 0]      # 回到中间
        ]
        
        for pose in poses:
            self._move_angles(pose, 45)
            time.sleep(0.6)
    
    def _question_gesture(self):
        """疑问手势（倾斜头部般的动作）"""
        poses = [
            [0, -30, -30, 0, 0, 0],     # 基础位置
            [15, -30, -30, 0, 0, 15],   # 向右倾斜
            [-15, -30, -30, 0, 0, -15], # 向左倾斜
            [0, -30, -30, 0, 0, 0]      # 回到基础位置
        ]
        
        for pose in poses:
            self._move_angles(pose, 40)
            time.sleep(0.7)
    
    def _thinking_gesture(self):
        """思考手势（模拟手托下巴）"""
        poses = [
            [0, -60, -90, 0, 60, 0],    # 手臂向上
            [0, -45, -75, 0, 45, 0],    # 模拟托下巴
        ]
        
        for pose in poses:
            self._move_angles(pose, 30)
            time.sleep(1.0)
        
        # 保持思考姿态2秒
        time.sleep(2.0)
        self._move_angles([0, 0, 0, 0, 0, 0], 40)
    
    def _demonstrate_counting(self, count: int = 5):
        """演示数数"""
        base_pose = [0, -45, -45, 0, 0, 0]
        
        for i in range(1, count + 1):
            # 每次数数时稍微改变角度
            counting_pose = base_pose.copy()
            counting_pose[5] = i * 15  # 旋转末端关节
            
            self._move_angles(counting_pose, 50)
            time.sleep(0.8)
        
        # 回到初始位置
        self._move_angles([0, 0, 0, 0, 0, 0], 50)
    
    def _demonstrate_shapes(self, shape: str = "circle"):
        """演示形状"""
        if shape == "circle":
            # 画圆形轨迹
            center = [200, 0, 200]
            radius = 50
            
            for angle in np.linspace(0, 2*np.pi, 12):
                x = center[0] + radius * np.cos(angle)
                y = center[1] + radius * np.sin(angle)
                z = center[2]
                
                coords = [x, y, z, 0, 90, 0]
                self._move_coords(coords, 30)
                time.sleep(0.3)
        
        elif shape == "square":
            # 画正方形轨迹
            corners = [
                [150, -50, 200], [250, -50, 200],
                [250, 50, 200], [150, 50, 200], [150, -50, 200]
            ]
            
            for corner in corners:
                coords = corner + [0, 90, 0]
                self._move_coords(coords, 40)
                time.sleep(0.5)
    
    def _demonstrate_directions(self, direction: str = "all"):
        """演示方向概念"""
        directions = {
            'up': [0, -30, -30, 0, 60, 0],
            'down': [0, -60, -90, 0, 30, 0],
            'left': [45, -45, -45, 0, 45, 0],
            'right': [-45, -45, -45, 0, 45, 0],
            'forward': [0, -30, -60, 0, 90, 0],
            'back': [0, -60, -30, 0, 30, 0]
        }
        
        if direction == "all":
            for dir_name, pose in directions.items():
                self._move_angles(pose, 40)
                time.sleep(1.0)
        else:
            if direction in directions:
                self._move_angles(directions[direction], 40)
                time.sleep(1.5)
        
        # 回到初始位置
        self._move_angles([0, 0, 0, 0, 0, 0], 40)
    
    def _demonstrate_sizes(self, sizes: List[str] = ["small", "medium", "large"]):
        """演示大小概念"""
        size_poses = {
            'small': [[0, -30, -60, 0, 45, 0], [0, -25, -55, 0, 40, 0]],
            'medium': [[0, -45, -75, 0, 60, 0], [0, -35, -65, 0, 50, 0]],
            'large': [[0, -60, -90, 0, 75, 0], [0, -45, -75, 0, 60, 0]]
        }
        
        for size in sizes:
            if size in size_poses:
                poses = size_poses[size]
                for pose in poses:
                    self._move_angles(pose, 35)
                    time.sleep(0.5)
                time.sleep(1.0)
        
        self._move_angles([0, 0, 0, 0, 0, 0], 40)
    
    def _demonstrate_writing(self, text: str = "Hello"):
        """演示书写动作"""
        # 简化的书写轨迹（实际需要更复杂的路径规划）
        writing_height = 180
        
        # 移动到书写起始位置
        start_pos = [100, -100, writing_height, 0, 90, 0]
        self._move_coords(start_pos, 40)
        time.sleep(0.5)
        
        # 模拟书写轨迹
        for i, char in enumerate(text.lower()):
            char_positions = self._get_char_trajectory(char, i * 30)
            
            for pos in char_positions:
                coords = [100 + pos[0], -100 + pos[1], writing_height, 0, 90, 0]
                self._move_coords(coords, 25)
                time.sleep(0.2)
        
        # 回到初始位置
        self._move_angles([0, 0, 0, 0, 0, 0], 40)
    
    def _get_char_trajectory(self, char: str, offset_x: float) -> List[Tuple[float, float]]:
        """
        获取字符的书写轨迹
        """
        # 简化的字符轨迹（实际应该更精确）
        trajectories = {
            'h': [(0, 0), (0, 20), (0, 10), (10, 10), (10, 0), (10, 20)],
            'e': [(0, 0), (15, 0), (0, 0), (0, 10), (10, 10), (0, 10), (0, 20), (15, 20)],
            'l': [(0, 0), (0, 20)],
            'o': [(0, 5), (0, 15), (5, 20), (10, 15), (10, 5), (5, 0), (0, 5)]
        }
        
        if char in trajectories:
            return [(offset_x + x, y) for x, y in trajectories[char]]
        else:
            return [(offset_x, 0), (offset_x + 10, 10)]  # 默认轨迹
    
    def _control_gripper(self, state: bool, speed: int = 50):
        """
        控制夹爪
        
        Args:
            state: True为闭合，False为张开
            speed: 速度
        """
        self.arm.set_gripper_state(1 if state else 0, speed)
        self.logger.debug(f"夹爪状态: {'闭合' if state else '张开'}")
    
    def _wait_for_completion(self):
        """
        等待动作完成
        """
        while self.arm.is_moving():
            time.sleep(0.1)
    
    def _validate_angles(self, angles: List[float]) -> bool:
        """
        验证关节角度是否在安全范围内
        """
        joint_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6']
        
        for i, angle in enumerate(angles):
            if i < len(joint_names):
                joint_name = joint_names[i]
                min_angle, max_angle = self.joint_limits[joint_name]
                
                if not (min_angle <= angle <= max_angle):
                    self.logger.warning(f"{joint_name} 角度超限: {angle} (范围: {min_angle}~{max_angle})")
                    return False
        
        return True
    
    def _validate_coordinates(self, coords: List[float]) -> bool:
        """
        验证坐标是否在工作空间内
        """
        x, y, z = coords[:3]
        
        for axis, value in [('x', x), ('y', y), ('z', z)]:
            min_val, max_val = self.workspace_limits[axis]
            if not (min_val <= value <= max_val):
                self.logger.warning(f"{axis}坐标超限: {value} (范围: {min_val}~{max_val})")
                return False
        
        return True
    
    def _validate_position(self, position: Tuple[float, float, float]) -> bool:
        """
        验证位置是否有效
        """
        return self._validate_coordinates(list(position))
    
    def _set_state(self, new_state: ArmState):
        """
        设置机械臂状态
        """
        if self.current_state != new_state:
            old_state = self.current_state
            self.current_state = new_state
            
            # 调用状态回调
            for callback in self.state_callbacks:
                try:
                    callback(old_state, new_state)
                except Exception as e:
                    self.logger.error(f"状态回调执行失败: {e}")
            
            self.logger.debug(f"机械臂状态变更: {old_state.value} -> {new_state.value}")
    
    def emergency_stop(self):
        """
        紧急停止
        """
        # 清空动作队列
        while not self.action_queue.empty():
            try:
                self.action_queue.get_nowait()
            except queue.Empty:
                break
        
        # 设置错误状态
        self._set_state(ArmState.ERROR)
        self.logger.warning("机械臂紧急停止")
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        """
        try:
            current_angles = self.arm.get_angles() if self.is_connected else [0] * 6
            current_coords = self.arm.get_coords() if self.is_connected else [0] * 6
        except:
            current_angles = [0] * 6
            current_coords = [0] * 6
        
        return {
            'state': self.current_state.value,
            'is_connected': self.is_connected,
            'current_angles': current_angles,
            'current_coordinates': current_coords,
            'queue_size': self.action_queue.qsize(),
            'is_moving': self.arm.is_moving() if self.is_connected else False
        }
    
    def add_action_callback(self, callback: Callable[[Dict], None]):
        """添加动作完成回调"""
        self.action_callbacks.append(callback)
    
    def add_state_callback(self, callback: Callable[[ArmState, ArmState], None]):
        """添加状态变更回调"""
        self.state_callbacks.append(callback)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.emergency_stop()
        self._stop_action_thread()