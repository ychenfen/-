"""
智能教育助手机器人主程序
整合所有模块，提供完整的教育助手功能
"""

import sys
import os
import time
import signal
import logging
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入各个模块
from vision.camera_manager import CameraManager
from vision.detector import ObjectDetector
from vision.ocr import OCRProcessor
from vision.face_analyzer import FaceAnalyzer

from audio.audio_manager import AudioManager

from llm.llm_engine import LLMEngine
from llm.knowledge_base import KnowledgeBase
from llm.dialogue_manager import DialogueManager

from fusion.multimodal_fusion import MultimodalFusionEngine, ModalityType
from control.robot_arm_controller import RobotArmController

@dataclass
class SystemStatus:
    """系统状态"""
    vision_active: bool = False
    audio_active: bool = False
    llm_active: bool = False
    arm_active: bool = False
    fusion_active: bool = False
    conversation_active: bool = False

class EducationalAssistantRobot:
    def __init__(self, config_path: str = None):
        """
        初始化智能教育助手机器人
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        self.status = SystemStatus()
        self.is_running = False
        
        # 初始化各个子系统
        self.camera_manager = None
        self.object_detector = None
        self.ocr_processor = None
        self.face_analyzer = None
        self.audio_manager = None
        self.llm_engine = None
        self.knowledge_base = None
        self.dialogue_manager = None
        self.fusion_engine = None
        self.arm_controller = None
        
        # 系统统计
        self.interaction_count = 0
        self.start_time = None
        
        self.logger.info("智能教育助手机器人初始化开始")
    
    def _setup_logging(self) -> logging.Logger:
        """
        设置日志系统
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('robot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置文件
        """
        default_config = {
            'vision': {
                'camera_id': 0,
                'resolution': (1280, 720),
                'detection_model': 'yolov8n.pt',
                'ocr_language': 'ch'
            },
            'audio': {
                'asr_model': 'small',
                'tts_rate': 200,
                'wake_words': ['小助手', '机器人', '你好']
            },
            'llm': {
                'model_name': 'Qwen/Qwen1.5-1.8B-Chat',
                'device': 'cpu',
                'use_onnx': False
            },
            'arm': {
                'port': '/dev/ttyUSB0',
                'baudrate': 115200
            },
            'fusion': {
                'strategy': 'weighted_average',
                'temporal_window': 2.0
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"配置文件加载失败，使用默认配置: {e}")
        
        return default_config
    
    def initialize_systems(self) -> bool:
        """
        初始化所有子系统
        
        Returns:
            是否全部初始化成功
        """
        try:
            self.logger.info("开始初始化各子系统...")
            
            # 1. 初始化视觉系统
            self._initialize_vision_system()
            
            # 2. 初始化音频系统  
            self._initialize_audio_system()
            
            # 3. 初始化LLM系统
            self._initialize_llm_system()
            
            # 4. 初始化多模态融合系统
            self._initialize_fusion_system()
            
            # 5. 初始化机械臂系统
            self._initialize_arm_system()
            
            # 6. 设置系统间回调
            self._setup_callbacks()
            
            self.logger.info("所有子系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            return False
    
    def _initialize_vision_system(self):
        """初始化视觉系统"""
        self.logger.info("初始化视觉系统...")
        
        vision_config = self.config['vision']
        
        # 摄像头管理器
        self.camera_manager = CameraManager(
            camera_id=vision_config['camera_id'],
            resolution=tuple(vision_config['resolution'])
        )
        
        # 目标检测器
        self.object_detector = ObjectDetector(
            model_path=vision_config['detection_model']
        )
        
        # OCR处理器
        self.ocr_processor = OCRProcessor(
            lang=vision_config['ocr_language']
        )
        
        # 人脸分析器
        self.face_analyzer = FaceAnalyzer()
        
        self.status.vision_active = True
        self.logger.info("视觉系统初始化完成")
    
    def _initialize_audio_system(self):
        """初始化音频系统"""
        self.logger.info("初始化音频系统...")
        
        audio_config = self.config['audio']
        
        # 音频管理器
        self.audio_manager = AudioManager(
            asr_model=audio_config['asr_model'],
            tts_rate=audio_config['tts_rate']
        )
        
        # 设置唤醒词
        self.audio_manager.set_wake_words(audio_config['wake_words'])
        
        self.status.audio_active = True
        self.logger.info("音频系统初始化完成")
    
    def _initialize_llm_system(self):
        """初始化LLM系统"""
        self.logger.info("初始化LLM系统...")
        
        llm_config = self.config['llm']
        
        # LLM推理引擎
        self.llm_engine = LLMEngine(
            model_name=llm_config['model_name'],
            device=llm_config['device'],
            use_onnx=llm_config['use_onnx']
        )
        
        # 知识库
        self.knowledge_base = KnowledgeBase()
        
        # 对话管理器
        self.dialogue_manager = DialogueManager(
            llm_engine=self.llm_engine,
            knowledge_base=self.knowledge_base
        )
        
        self.status.llm_active = True
        self.logger.info("LLM系统初始化完成")
    
    def _initialize_fusion_system(self):
        """初始化多模态融合系统"""
        self.logger.info("初始化多模态融合系统...")
        
        fusion_config = self.config['fusion']
        
        # 多模态融合引擎
        self.fusion_engine = MultimodalFusionEngine(
            fusion_strategy=fusion_config['strategy'],
            temporal_window=fusion_config['temporal_window']
        )
        
        self.status.fusion_active = True
        self.logger.info("多模态融合系统初始化完成")
    
    def _initialize_arm_system(self):
        """初始化机械臂系统"""
        self.logger.info("初始化机械臂系统...")
        
        try:
            arm_config = self.config['arm']
            
            # 机械臂控制器
            self.arm_controller = RobotArmController(
                port=arm_config['port'],
                baudrate=arm_config['baudrate']
            )
            
            self.status.arm_active = True
            self.logger.info("机械臂系统初始化完成")
            
        except Exception as e:
            self.logger.warning(f"机械臂初始化失败，将在模拟模式下运行: {e}")
            self.status.arm_active = False
    
    def _setup_callbacks(self):
        """设置系统间回调"""
        self.logger.info("设置系统间回调...")
        
        # 音频系统回调
        self.audio_manager.add_speech_recognized_callback(self._on_speech_recognized)
        self.audio_manager.add_wake_word_detected_callback(self._on_wake_word_detected)
        self.audio_manager.add_conversation_started_callback(self._on_conversation_started)
        self.audio_manager.add_conversation_ended_callback(self._on_conversation_ended)
        
        # 摄像头回调
        self.camera_manager.add_frame_callback(self._on_frame_received)
        
        # 融合引擎回调
        self.fusion_engine.add_fusion_callback(self._on_fusion_result)
    
    def start_system(self) -> bool:
        """
        启动系统
        
        Returns:
            是否启动成功
        """
        try:
            self.logger.info("启动智能教育助手机器人...")
            self.start_time = time.time()
            self.is_running = True
            
            # 启动摄像头流
            if self.status.vision_active:
                self.camera_manager.start_streaming()
            
            # 启动音频监听
            if self.status.audio_active:
                self.audio_manager.start_listening()
            
            # 初始问候
            self._initial_greeting()
            
            self.logger.info("智能教育助手机器人启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def stop_system(self):
        """停止系统"""
        self.logger.info("停止智能教育助手机器人...")
        self.is_running = False
        
        # 停止各个子系统
        if self.camera_manager:
            self.camera_manager.stop_streaming()
        
        if self.audio_manager:
            self.audio_manager.stop_listening()
        
        if self.arm_controller:
            self.arm_controller.emergency_stop()
        
        # 输出运行统计
        if self.start_time:
            runtime = time.time() - self.start_time
            self.logger.info(f"运行时长: {runtime:.1f}秒，交互次数: {self.interaction_count}")
        
        self.logger.info("系统已停止")
    
    def _initial_greeting(self):
        """初始问候"""
        greeting_messages = [
            "你好！我是智能教育助手机器人，很高兴为你服务！",
            "我可以帮助你学习各种知识，回答问题，还能用手势来演示概念。",
            "你可以说'小助手'来唤醒我，然后我们就可以开始学习了！"
        ]
        
        if self.status.audio_active:
            for message in greeting_messages:
                self.audio_manager.speak(message, priority="normal", emotion="happy")
                time.sleep(2)
        
        if self.status.arm_active:
            # 执行问候手势
            self.arm_controller.perform_educational_gesture("greeting")
    
    def _on_speech_recognized(self, recognition_result: Dict[str, Any]):
        """
        语音识别回调
        
        Args:
            recognition_result: 识别结果
        """
        text = recognition_result.get('text', '')
        confidence = recognition_result.get('confidence', 0.0)
        
        self.logger.info(f"语音识别: {text} (置信度: {confidence:.2f})")
        
        # 添加到多模态融合
        audio_data = {
            'text': text,
            'confidence': confidence,
            'language': recognition_result.get('language', 'zh')
        }
        
        self.fusion_engine.add_audio_input(audio_data, confidence)
        
        # 更新交互统计
        self.interaction_count += 1
    
    def _on_wake_word_detected(self, wake_word: str):
        """
        唤醒词检测回调
        """
        self.logger.info(f"检测到唤醒词: {wake_word}")
        
        # 执行注意手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("greeting")
        
        # 语音回应
        if self.status.audio_active:
            responses = [
                f"我听到你叫我了！有什么可以帮助你的吗？",
                f"我在这里！准备好学习了吗？",
                f"你好！我是你的学习助手，需要什么帮助？"
            ]
            
            import random
            response = random.choice(responses)
            self.audio_manager.speak(response, priority="high", emotion="excited")
    
    def _on_conversation_started(self):
        """对话开始回调"""
        self.logger.info("对话模式开始")
        self.status.conversation_active = True
        
        # 开始对话会话
        if self.dialogue_manager:
            self.dialogue_manager.start_session()
        
        # 执行欢迎手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("encouragement")
    
    def _on_conversation_ended(self):
        """对话结束回调"""
        self.logger.info("对话模式结束")
        self.status.conversation_active = False
        
        # 结束对话会话
        if self.dialogue_manager:
            session_info = self.dialogue_manager.end_session()
            
            # 播放总结
            if self.status.audio_active:
                summary = session_info.get('summary', '感谢你的学习！')
                self.audio_manager.speak(summary, emotion="calm")
        
        # 执行告别手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("greeting")
    
    def _on_frame_received(self, frame):
        """
        接收到新帧的回调
        
        Args:
            frame: 视频帧
        """
        try:
            # 目标检测
            objects = self.object_detector.detect_educational_objects(frame)
            
            # OCR识别
            text_results = self.ocr_processor.recognize_text(frame)
            
            # 人脸分析
            attention_info = self.face_analyzer.analyze_attention(frame)
            
            # 组装视觉数据
            vision_data = {
                'objects': objects,
                'text': text_results,
                'attention': attention_info,
                'timestamp': time.time()
            }
            
            # 计算总体置信度
            confidence = 0.7  # 基础置信度
            if objects.get('books') or objects.get('writing_tools'):
                confidence += 0.1
            if text_results:
                confidence += 0.1
            if attention_info.get('attention_score', 0) > 0.5:
                confidence += 0.1
            
            # 添加到多模态融合
            self.fusion_engine.add_vision_input(vision_data, min(confidence, 1.0))
            
        except Exception as e:
            self.logger.error(f"视频帧处理失败: {e}")
    
    def _on_fusion_result(self, fusion_result):
        """
        多模态融合结果回调
        
        Args:
            fusion_result: 融合结果
        """
        intent = fusion_result.primary_intent
        confidence = fusion_result.confidence
        features = fusion_result.combined_features
        
        self.logger.info(f"融合结果 - 意图: {intent}, 置信度: {confidence:.2f}")
        
        # 根据融合结果执行相应动作
        if confidence > 0.5:
            self._handle_fused_intent(intent, features, confidence)
    
    def _handle_fused_intent(self, intent: str, features: Dict, confidence: float):
        """
        处理融合意图
        
        Args:
            intent: 识别的意图
            features: 特征信息
            confidence: 置信度
        """
        try:
            if intent == 'learning_request':
                self._handle_learning_request(features)
            
            elif intent == 'question_asking':
                self._handle_question_asking(features)
            
            elif intent == 'attention_seeking':
                self._handle_attention_seeking(features)
            
            elif intent == 'practice_request':
                self._handle_practice_request(features)
            
            elif intent == 'confirmation':
                self._handle_confirmation(features)
            
            elif intent == 'confusion':
                self._handle_confusion(features)
            
            else:
                self.logger.debug(f"未处理的意图: {intent}")
                
        except Exception as e:
            self.logger.error(f"处理融合意图失败: {e}")
    
    def _handle_learning_request(self, features: Dict):
        """处理学习请求"""
        self.logger.info("处理学习请求")
        
        # 获取用户输入文本
        user_text = ""
        if 'audio' in features:
            audio_summary = features['audio']['data_summary']
            user_text = audio_summary.get('text', '')
        
        # 如果有视觉内容，结合分析
        visual_context = ""
        if 'vision' in features:
            vision_summary = features['vision']['data_summary']
            if vision_summary.get('text_detected'):
                visual_context = "我看到你有一些文字材料，"
            if vision_summary.get('object_count', 0) > 0:
                visual_context += "我注意到你有一些学习用品，"
        
        # 生成教育回复
        if self.dialogue_manager and user_text:
            enhanced_prompt = visual_context + user_text
            response = self.dialogue_manager.process_user_input(enhanced_prompt)
            
            # 语音回复
            if self.status.audio_active:
                self.audio_manager.speak_educational_content(
                    response['response']['text'], 
                    'explanation'
                )
            
            # 相应手势
            if self.status.arm_active:
                self.arm_controller.perform_educational_gesture("explanation")
    
    def _handle_question_asking(self, features: Dict):
        """处理提问"""
        self.logger.info("处理学生提问")
        
        # 执行思考手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("thinking")
        
        # 处理问题（逻辑与learning_request类似）
        self._handle_learning_request(features)
    
    def _handle_attention_seeking(self, features: Dict):
        """处理注意力引导"""
        self.logger.info("处理注意力引导")
        
        # 执行注意手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("pointing")
        
        # 鼓励性语音
        if self.status.audio_active:
            encouragements = [
                "来，我们一起专心学习吧！",
                "注意看这里，有很有趣的内容呢！",
                "专注一点，你一定能学会的！"
            ]
            
            import random
            message = random.choice(encouragements)
            self.audio_manager.speak(message, emotion="encouraging")
    
    def _handle_practice_request(self, features: Dict):
        """处理练习请求"""
        self.logger.info("处理练习请求")
        
        # 执行问题手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("question")
        
        # 提供练习内容
        if self.status.audio_active:
            practice_intro = "好的，让我们来做一些练习吧！"
            self.audio_manager.speak_educational_content(practice_intro, 'question')
    
    def _handle_confirmation(self, features: Dict):
        """处理确认回应"""
        self.logger.info("处理学生确认")
        
        # 执行鼓励手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("encouragement")
        
        # 鼓励性回复
        if self.status.audio_active:
            confirmations = [
                "很好！你理解得很正确！",
                "太棒了！继续保持这样的学习状态！",
                "优秀！你掌握得很不错！"
            ]
            
            import random
            message = random.choice(confirmations)
            self.audio_manager.speak(message, emotion="happy")
    
    def _handle_confusion(self, features: Dict):
        """处理困惑状态"""
        self.logger.info("处理学生困惑")
        
        # 执行解释手势
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("explanation")
        
        # 耐心解释
        if self.status.audio_active:
            comfort_messages = [
                "没关系，让我用更简单的方式来解释一下。",
                "不要担心，学习是一个过程，我们慢慢来。",
                "我换个角度来说明，相信你一定能明白。"
            ]
            
            import random
            message = random.choice(comfort_messages)
            self.audio_manager.speak(message, emotion="calm")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态信息
        """
        status_info = {
            'is_running': self.is_running,
            'uptime': time.time() - self.start_time if self.start_time else 0,
            'interaction_count': self.interaction_count,
            'subsystems': {
                'vision': self.status.vision_active,
                'audio': self.status.audio_active,
                'llm': self.status.llm_active,
                'fusion': self.status.fusion_active,
                'arm': self.status.arm_active
            },
            'conversation_active': self.status.conversation_active
        }
        
        # 添加详细状态
        if self.audio_manager:
            status_info['audio_status'] = self.audio_manager.get_audio_status()
        
        if self.arm_controller:
            status_info['arm_status'] = self.arm_controller.get_current_status()
        
        if self.fusion_engine:
            status_info['fusion_status'] = self.fusion_engine.get_fusion_status()
        
        return status_info
    
    def run_demonstration(self):
        """
        运行演示程序
        """
        self.logger.info("开始运行演示程序")
        
        try:
            # 1. 系统介绍
            self._demo_system_introduction()
            
            # 2. 视觉功能演示
            self._demo_vision_capabilities()
            
            # 3. 语音交互演示
            self._demo_audio_interaction()
            
            # 4. 机械臂动作演示
            self._demo_arm_movements()
            
            # 5. 教育场景演示
            self._demo_educational_scenarios()
            
            # 6. 多模态融合演示
            self._demo_multimodal_fusion()
            
            self.logger.info("演示程序完成")
            
        except KeyboardInterrupt:
            self.logger.info("演示程序被用户中断")
        except Exception as e:
            self.logger.error(f"演示程序执行失败: {e}")
    
    def _demo_system_introduction(self):
        """演示系统介绍"""
        self.logger.info("=== 系统介绍演示 ===")
        
        introduction = [
            "欢迎体验智能教育助手机器人！",
            "我是基于RISC-V K1芯片的多模态AI教育助手。",
            "我具备视觉识别、语音交互、知识问答和机械臂操作能力。",
            "让我为你展示我的各项功能吧！"
        ]
        
        for message in introduction:
            if self.status.audio_active:
                self.audio_manager.speak(message, emotion="excited")
                time.sleep(3)
        
        if self.status.arm_active:
            self.arm_controller.perform_educational_gesture("greeting")
    
    def _demo_vision_capabilities(self):
        """演示视觉功能"""
        self.logger.info("=== 视觉功能演示 ===")
        
        if self.status.audio_active:
            self.audio_manager.speak("现在展示我的视觉识别能力", emotion="neutral")
            time.sleep(2)
            
            capabilities = [
                "我可以检测和识别各种物体，特别是学习用品",
                "我能识别图片中的文字内容，支持中英文OCR",
                "我可以分析学生的面部表情和专注度",
                "请在摄像头前放置一些书本或写字的纸张，我来识别看看"
            ]
            
            for capability in capabilities:
                self.audio_manager.speak(capability, emotion="explanation")
                time.sleep(4)
        
        # 等待用户放置物品进行识别
        self.logger.info("等待视觉识别演示...")
        time.sleep(10)
    
    def _demo_audio_interaction(self):
        """演示语音交互"""
        self.logger.info("=== 语音交互演示 ===")
        
        if self.status.audio_active:
            demo_messages = [
                "接下来展示语音交互功能",
                "我支持中文语音识别，可以理解你的问题",
                "我的语音合成支持情感表达，让对话更自然",
                "你可以说'小助手'来唤醒我，然后问我任何学习问题",
                "比如你可以问：什么是人工智能？或者：帮我解释一下数学公式"
            ]
            
            for message in demo_messages:
                self.audio_manager.speak(message, emotion="explanation")
                time.sleep(4)
        
        # 启动语音监听等待用户交互
        self.logger.info("语音交互演示就绪，等待用户输入...")
        time.sleep(15)
    
    def _demo_arm_movements(self):
        """演示机械臂动作"""
        self.logger.info("=== 机械臂动作演示 ===")
        
        if not self.status.arm_active:
            if self.status.audio_active:
                self.audio_manager.speak("机械臂未连接，跳过动作演示", emotion="neutral")
            return
        
        if self.status.audio_active:
            self.audio_manager.speak("现在演示机械臂的各种教育手势", emotion="excited")
            time.sleep(2)
        
        # 演示各种手势
        gestures = [
            ("greeting", "问候手势"),
            ("pointing", "指向手势"),
            ("encouragement", "鼓励手势"),
            ("explanation", "解释手势"),
            ("thinking", "思考手势")
        ]
        
        for gesture_name, description in gestures:
            if self.status.audio_active:
                self.audio_manager.speak(f"这是{description}", emotion="neutral")
                time.sleep(1)
            
            self.arm_controller.perform_educational_gesture(gesture_name)
            time.sleep(3)
        
        # 演示教学概念
        if self.status.audio_active:
            self.audio_manager.speak("现在演示一些教学概念", emotion="explanation")
            time.sleep(2)
        
        concepts = [
            ("counting", "数数概念"),
            ("directions", "方向概念"),
            ("shapes", "几何形状")
        ]
        
        for concept_name, description in concepts:
            if self.status.audio_active:
                self.audio_manager.speak(f"演示{description}", emotion="neutral")
                time.sleep(1)
            
            self.arm_controller.demonstrate_concept(concept_name)
            time.sleep(5)
    
    def _demo_educational_scenarios(self):
        """演示教育场景"""
        self.logger.info("=== 教育场景演示 ===")
        
        scenarios = [
            {
                'name': '数学学习',
                'question': '请帮我解释什么是加法',
                'subject': 'math'
            },
            {
                'name': '语文学习', 
                'question': '什么是诗歌的韵律',
                'subject': 'chinese'
            },
            {
                'name': '英语学习',
                'question': 'What is the difference between "a" and "an"?',
                'subject': 'english'
            }
        ]
        
        for scenario in scenarios:
            self.logger.info(f"演示场景: {scenario['name']}")
            
            if self.status.audio_active:
                self.audio_manager.speak(f"现在演示{scenario['name']}场景", emotion="excited")
                time.sleep(2)
                
                # 模拟学生提问
                self.audio_manager.speak("模拟学生提问：" + scenario['question'], emotion="question")
                time.sleep(2)
            
            # 生成教育回复
            if self.dialogue_manager:
                response = self.llm_engine.generate_educational_response(
                    scenario['question'], 
                    scenario['subject'],
                    'medium'
                )
                
                if self.status.audio_active:
                    self.audio_manager.speak_educational_content(
                        response['text'], 
                        'explanation'
                    )
                
                if self.status.arm_active:
                    self.arm_controller.perform_educational_gesture("explanation")
            
            time.sleep(8)
    
    def _demo_multimodal_fusion(self):
        """演示多模态融合"""
        self.logger.info("=== 多模态融合演示 ===")
        
        if self.status.audio_active:
            fusion_demo = [
                "最后演示我的核心能力：多模态信息融合",
                "我可以同时处理视觉、语音和文本信息",
                "通过AI算法将多种感知模态整合，做出智能决策",
                "比如：看到学习材料 + 听到提问 + 分析学习状态 = 提供个性化教学"
            ]
            
            for message in fusion_demo:
                self.audio_manager.speak(message, emotion="explanation")
                time.sleep(5)
        
        # 显示融合状态
        if self.fusion_engine:
            status = self.fusion_engine.get_fusion_status()
            self.logger.info(f"融合引擎状态: {status}")
    

def signal_handler(signum, frame):
    """信号处理器"""
    print("\\n接收到停止信号，正在关闭系统...")
    global robot
    if robot:
        robot.stop_system()
    sys.exit(0)

def main():
    """主函数"""
    global robot
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("智能教育助手机器人 - 蓝桥杯参赛作品")
    print("基于RISC-V K1芯片的多模态AI教育系统")
    print("=" * 60)
    
    try:
        # 创建机器人实例
        robot = EducationalAssistantRobot()
        
        # 初始化系统
        if not robot.initialize_systems():
            print("系统初始化失败，程序退出")
            return
        
        # 启动系统
        if not robot.start_system():
            print("系统启动失败，程序退出")
            return
        
        # 选择运行模式
        print("\\n请选择运行模式:")
        print("1. 正常运行模式")
        print("2. 演示模式")
        print("3. 状态监控模式")
        
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == "1":
            # 正常运行模式
            print("系统已启动，按 Ctrl+C 退出")
            while robot.is_running:
                time.sleep(1)
                
        elif choice == "2":
            # 演示模式
            robot.run_demonstration()
            
        elif choice == "3":
            # 状态监控模式
            print("状态监控模式，每5秒更新一次状态")
            while robot.is_running:
                status = robot.get_system_status()
                print(f"\\n系统状态: 运行时间 {status['uptime']:.1f}s, 交互次数 {status['interaction_count']}")
                print(f"子系统: 视觉={status['subsystems']['vision']}, 音频={status['subsystems']['audio']}, LLM={status['subsystems']['llm']}")
                print(f"机械臂={status['subsystems']['arm']}, 融合={status['subsystems']['fusion']}")
                time.sleep(5)
        
        else:
            print("无效选择，使用正常运行模式")
            while robot.is_running:
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\\n用户中断程序")
    except Exception as e:
        print(f"程序运行错误: {e}")
    finally:
        if robot:
            robot.stop_system()

if __name__ == "__main__":
    main()