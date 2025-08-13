"""
多模态融合引擎
整合视觉、语音、文本等多种模态信息，生成统一的语义理解
"""

import numpy as np
import threading
import queue
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging

class ModalityType(Enum):
    """模态类型枚举"""
    VISION = "vision"
    AUDIO = "audio" 
    TEXT = "text"
    ACTION = "action"

@dataclass
class ModalityInput:
    """模态输入数据结构"""
    modality_type: ModalityType
    data: Any
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = None

@dataclass
class FusionResult:
    """融合结果数据结构"""
    primary_intent: str
    confidence: float
    modality_weights: Dict[ModalityType, float]
    combined_features: Dict[str, Any]
    context_info: Dict[str, Any]
    timestamp: float

class MultimodalFusionEngine:
    def __init__(self, 
                 fusion_strategy: str = "weighted_average",
                 temporal_window: float = 2.0,
                 confidence_threshold: float = 0.3):
        """
        初始化多模态融合引擎
        
        Args:
            fusion_strategy: 融合策略 ("weighted_average", "attention", "rule_based")
            temporal_window: 时间窗口大小（秒）
            confidence_threshold: 置信度阈值
        """
        self.logger = logging.getLogger(__name__)
        self.fusion_strategy = fusion_strategy
        self.temporal_window = temporal_window
        self.confidence_threshold = confidence_threshold
        
        # 模态输入队列
        self.modality_queues = {
            ModalityType.VISION: queue.Queue(),
            ModalityType.AUDIO: queue.Queue(),
            ModalityType.TEXT: queue.Queue(),
            ModalityType.ACTION: queue.Queue()
        }
        
        # 融合结果回调
        self.fusion_callbacks = []
        
        # 时间窗口缓存
        self.temporal_cache = {}
        self.cache_lock = threading.Lock()
        
        # 融合权重（可动态调整）
        self.modality_weights = {
            ModalityType.VISION: 0.3,
            ModalityType.AUDIO: 0.4,
            ModalityType.TEXT: 0.3,
            ModalityType.ACTION: 0.0  # 默认动作权重为0
        }
        
        # 教育场景的语义映射
        self.educational_intents = {
            'learning_request': ['学习', '教', '解释', '什么是'],
            'question_asking': ['为什么', '怎么', '如何', '?', '？'],
            'confirmation': ['对', '是的', '正确', '明白'],
            'confusion': ['不懂', '不明白', '困惑', '难'],
            'attention_seeking': ['看这里', '注意', '重要'],
            'practice_request': ['练习', '题目', '测试', '做题']
        }
        
        # 启动融合处理线程
        self.is_running = False
        self.fusion_thread = None
        self._start_fusion_thread()
        
        self.logger.info(f"多模态融合引擎初始化成功，策略: {fusion_strategy}")
    
    def add_modality_input(self, modality_input: ModalityInput):
        """
        添加模态输入
        
        Args:
            modality_input: 模态输入数据
        """
        try:
            # 过滤低置信度输入
            if modality_input.confidence < self.confidence_threshold:
                self.logger.debug(f"跳过低置信度输入: {modality_input.modality_type.value}")
                return
            
            # 添加到对应的队列
            self.modality_queues[modality_input.modality_type].put(modality_input)
            
            # 更新时间窗口缓存
            self._update_temporal_cache(modality_input)
            
            self.logger.debug(f"添加模态输入: {modality_input.modality_type.value}")
            
        except Exception as e:
            self.logger.error(f"添加模态输入失败: {e}")
    
    def add_vision_input(self, vision_data: Dict[str, Any], confidence: float = 0.8):
        """
        添加视觉输入
        
        Args:
            vision_data: 视觉数据（检测结果、OCR结果等）
            confidence: 置信度
        """
        modality_input = ModalityInput(
            modality_type=ModalityType.VISION,
            data=vision_data,
            confidence=confidence,
            timestamp=time.time(),
            metadata={'source': 'vision_system'}
        )
        self.add_modality_input(modality_input)
    
    def add_audio_input(self, audio_data: Dict[str, Any], confidence: float = 0.8):
        """
        添加语音输入
        
        Args:
            audio_data: 语音数据（ASR结果等）
            confidence: 置信度
        """
        modality_input = ModalityInput(
            modality_type=ModalityType.AUDIO,
            data=audio_data,
            confidence=confidence,
            timestamp=time.time(),
            metadata={'source': 'audio_system'}
        )
        self.add_modality_input(modality_input)
    
    def add_text_input(self, text_data: Dict[str, Any], confidence: float = 0.9):
        """
        添加文本输入
        
        Args:
            text_data: 文本数据（LLM结果等）
            confidence: 置信度
        """
        modality_input = ModalityInput(
            modality_type=ModalityType.TEXT,
            data=text_data,
            confidence=confidence,
            timestamp=time.time(),
            metadata={'source': 'text_system'}
        )
        self.add_modality_input(modality_input)
    
    def _start_fusion_thread(self):
        """
        启动融合处理线程
        """
        if self.fusion_thread and self.fusion_thread.is_alive():
            return
        
        self.is_running = True
        self.fusion_thread = threading.Thread(target=self._fusion_worker)
        self.fusion_thread.daemon = True
        self.fusion_thread.start()
    
    def _stop_fusion_thread(self):
        """
        停止融合处理线程
        """
        self.is_running = False
        if self.fusion_thread:
            self.fusion_thread.join(timeout=2.0)
    
    def _fusion_worker(self):
        """
        融合处理工作线程
        """
        while self.is_running:
            try:
                # 收集时间窗口内的所有模态输入
                modality_inputs = self._collect_temporal_inputs()
                
                if modality_inputs:
                    # 执行多模态融合
                    fusion_result = self._perform_fusion(modality_inputs)
                    
                    if fusion_result:
                        # 调用回调函数
                        for callback in self.fusion_callbacks:
                            try:
                                callback(fusion_result)
                            except Exception as e:
                                self.logger.error(f"融合回调执行失败: {e}")
                
                # 清理过期缓存
                self._cleanup_temporal_cache()
                
                time.sleep(0.1)  # 100ms处理周期
                
            except Exception as e:
                self.logger.error(f"融合处理工作线程错误: {e}")
    
    def _update_temporal_cache(self, modality_input: ModalityInput):
        """
        更新时间窗口缓存
        
        Args:
            modality_input: 模态输入
        """
        with self.cache_lock:
            modality_type = modality_input.modality_type
            
            if modality_type not in self.temporal_cache:
                self.temporal_cache[modality_type] = []
            
            self.temporal_cache[modality_type].append(modality_input)
    
    def _collect_temporal_inputs(self) -> Dict[ModalityType, List[ModalityInput]]:
        """
        收集时间窗口内的输入
        
        Returns:
            时间窗口内的模态输入
        """
        current_time = time.time()
        temporal_inputs = {}
        
        with self.cache_lock:
            for modality_type, inputs in self.temporal_cache.items():
                # 过滤时间窗口内的输入
                valid_inputs = [
                    inp for inp in inputs 
                    if current_time - inp.timestamp <= self.temporal_window
                ]
                
                if valid_inputs:
                    temporal_inputs[modality_type] = valid_inputs
        
        return temporal_inputs
    
    def _cleanup_temporal_cache(self):
        """
        清理过期缓存
        """
        current_time = time.time()
        
        with self.cache_lock:
            for modality_type in self.temporal_cache:
                self.temporal_cache[modality_type] = [
                    inp for inp in self.temporal_cache[modality_type]
                    if current_time - inp.timestamp <= self.temporal_window * 2
                ]
    
    def _perform_fusion(self, modality_inputs: Dict[ModalityType, List[ModalityInput]]) -> Optional[FusionResult]:
        """
        执行多模态融合
        
        Args:
            modality_inputs: 模态输入字典
            
        Returns:
            融合结果
        """
        try:
            if self.fusion_strategy == "weighted_average":
                return self._weighted_average_fusion(modality_inputs)
            elif self.fusion_strategy == "attention":
                return self._attention_fusion(modality_inputs)
            elif self.fusion_strategy == "rule_based":
                return self._rule_based_fusion(modality_inputs)
            else:
                self.logger.error(f"未知融合策略: {self.fusion_strategy}")
                return None
                
        except Exception as e:
            self.logger.error(f"多模态融合失败: {e}")
            return None
    
    def _weighted_average_fusion(self, modality_inputs: Dict[ModalityType, List[ModalityInput]]) -> FusionResult:
        """
        加权平均融合策略
        
        Args:
            modality_inputs: 模态输入
            
        Returns:
            融合结果
        """
        intent_scores = {}
        combined_features = {}
        total_weight = 0
        
        # 计算每个模态的贡献
        for modality_type, inputs in modality_inputs.items():
            if not inputs:
                continue
            
            # 获取最新的输入
            latest_input = max(inputs, key=lambda x: x.timestamp)
            modality_weight = self.modality_weights.get(modality_type, 0.0)
            
            # 提取意图和特征
            intent_info = self._extract_intent_from_modality(latest_input)
            features = self._extract_features_from_modality(latest_input)
            
            # 累加意图分数
            for intent, score in intent_info.items():
                if intent not in intent_scores:
                    intent_scores[intent] = 0
                intent_scores[intent] += score * modality_weight * latest_input.confidence
            
            # 合并特征
            combined_features[modality_type.value] = features
            total_weight += modality_weight
        
        # 归一化意图分数
        if total_weight > 0:
            for intent in intent_scores:
                intent_scores[intent] /= total_weight
        
        # 选择最高分意图
        primary_intent = max(intent_scores.items(), key=lambda x: x[1]) if intent_scores else ("unknown", 0.0)
        
        # 构建融合结果
        fusion_result = FusionResult(
            primary_intent=primary_intent[0],
            confidence=primary_intent[1],
            modality_weights=self.modality_weights.copy(),
            combined_features=combined_features,
            context_info=self._build_context_info(modality_inputs),
            timestamp=time.time()
        )
        
        self.logger.debug(f"融合结果 - 意图: {primary_intent[0]}, 置信度: {primary_intent[1]:.2f}")
        return fusion_result
    
    def _attention_fusion(self, modality_inputs: Dict[ModalityType, List[ModalityInput]]) -> FusionResult:
        """
        注意力机制融合策略
        
        Args:
            modality_inputs: 模态输入
            
        Returns:
            融合结果
        """
        # 简化的注意力机制实现
        attention_weights = {}
        total_attention = 0
        
        # 计算注意力权重
        for modality_type, inputs in modality_inputs.items():
            if not inputs:
                continue
            
            latest_input = max(inputs, key=lambda x: x.timestamp)
            
            # 基于置信度和新鲜度计算注意力
            freshness = 1.0 / (1.0 + (time.time() - latest_input.timestamp))
            attention = latest_input.confidence * freshness
            
            attention_weights[modality_type] = attention
            total_attention += attention
        
        # 归一化注意力权重
        if total_attention > 0:
            for modality_type in attention_weights:
                attention_weights[modality_type] /= total_attention
        
        # 使用注意力权重进行融合
        # 这里复用加权平均的逻辑，但使用注意力权重
        original_weights = self.modality_weights.copy()
        self.modality_weights.update({k: v for k, v in attention_weights.items()})
        
        result = self._weighted_average_fusion(modality_inputs)
        
        # 恢复原始权重
        self.modality_weights = original_weights
        
        return result
    
    def _rule_based_fusion(self, modality_inputs: Dict[ModalityType, List[ModalityInput]]) -> FusionResult:
        """
        基于规则的融合策略
        
        Args:
            modality_inputs: 模态输入
            
        Returns:
            融合结果
        """
        # 教育场景的融合规则
        primary_intent = "unknown"
        confidence = 0.0
        combined_features = {}
        
        # 规则1: 如果有明确的语音指令，优先处理
        if ModalityType.AUDIO in modality_inputs:
            audio_inputs = modality_inputs[ModalityType.AUDIO]
            latest_audio = max(audio_inputs, key=lambda x: x.timestamp)
            
            if latest_audio.confidence > 0.7:
                audio_intent = self._extract_intent_from_modality(latest_audio)
                if audio_intent:
                    primary_intent = max(audio_intent.items(), key=lambda x: x[1])[0]
                    confidence = latest_audio.confidence
        
        # 规则2: 如果视觉检测到学习材料，结合语音进行解释
        if ModalityType.VISION in modality_inputs and ModalityType.AUDIO in modality_inputs:
            vision_inputs = modality_inputs[ModalityType.VISION]
            latest_vision = max(vision_inputs, key=lambda x: x.timestamp)
            
            vision_data = latest_vision.data
            if 'objects' in vision_data or 'text' in vision_data:
                if primary_intent in ['unknown', 'general_inquiry']:
                    primary_intent = 'learning_request'
                    confidence = max(confidence, 0.8)
        
        # 规则3: 如果检测到学生困惑表情或语音，提供鼓励
        if ModalityType.VISION in modality_inputs:
            vision_inputs = modality_inputs[ModalityType.VISION]
            latest_vision = max(vision_inputs, key=lambda x: x.timestamp)
            
            vision_data = latest_vision.data
            if 'attention' in vision_data:
                attention_info = vision_data['attention']
                if attention_info.get('engagement_level') == 'low':
                    primary_intent = 'attention_seeking'
                    confidence = max(confidence, 0.6)
        
        # 提取特征
        for modality_type, inputs in modality_inputs.items():
            if inputs:
                latest_input = max(inputs, key=lambda x: x.timestamp)
                combined_features[modality_type.value] = self._extract_features_from_modality(latest_input)
        
        return FusionResult(
            primary_intent=primary_intent,
            confidence=confidence,
            modality_weights=self.modality_weights.copy(),
            combined_features=combined_features,
            context_info=self._build_context_info(modality_inputs),
            timestamp=time.time()
        )
    
    def _extract_intent_from_modality(self, modality_input: ModalityInput) -> Dict[str, float]:
        """
        从模态输入中提取意图
        
        Args:
            modality_input: 模态输入
            
        Returns:
            意图分数字典
        """
        intent_scores = {}
        
        if modality_input.modality_type == ModalityType.AUDIO:
            # 从语音识别结果提取意图
            audio_data = modality_input.data
            if 'text' in audio_data:
                text = audio_data['text'].lower()
                
                for intent, keywords in self.educational_intents.items():
                    score = sum(1 for keyword in keywords if keyword in text)
                    if score > 0:
                        intent_scores[intent] = score / len(keywords)
        
        elif modality_input.modality_type == ModalityType.VISION:
            # 从视觉检测结果提取意图
            vision_data = modality_input.data
            
            if 'objects' in vision_data:
                # 检测到学习相关物品
                objects = vision_data['objects']
                educational_objects = ['book', 'paper', 'pen', 'laptop']
                
                if any(obj['class_name'] in educational_objects for obj in objects):
                    intent_scores['learning_request'] = 0.6
            
            if 'text' in vision_data:
                # 检测到文字内容
                intent_scores['learning_request'] = 0.7
            
            if 'attention' in vision_data:
                # 专注度分析
                attention_info = vision_data['attention']
                engagement = attention_info.get('engagement_level', 'medium')
                
                if engagement == 'low':
                    intent_scores['attention_seeking'] = 0.8
        
        elif modality_input.modality_type == ModalityType.TEXT:
            # 从文本输入提取意图
            text_data = modality_input.data
            if 'intent' in text_data:
                intent_scores[text_data['intent']] = text_data.get('confidence', 0.8)
        
        return intent_scores
    
    def _extract_features_from_modality(self, modality_input: ModalityInput) -> Dict[str, Any]:
        """
        从模态输入中提取特征
        
        Args:
            modality_input: 模态输入
            
        Returns:
            特征字典
        """
        features = {
            'confidence': modality_input.confidence,
            'timestamp': modality_input.timestamp,
            'data_summary': {}
        }
        
        data = modality_input.data
        
        if modality_input.modality_type == ModalityType.AUDIO:
            features['data_summary'] = {
                'has_speech': 'text' in data,
                'text_length': len(data.get('text', '')) if 'text' in data else 0,
                'language': data.get('language', 'unknown')
            }
        
        elif modality_input.modality_type == ModalityType.VISION:
            features['data_summary'] = {
                'object_count': len(data.get('objects', [])),
                'text_detected': 'text' in data,
                'face_count': data.get('faces', {}).get('count', 0),
                'attention_score': data.get('attention', {}).get('attention_score', 0.0)
            }
        
        elif modality_input.modality_type == ModalityType.TEXT:
            features['data_summary'] = {
                'text_length': len(str(data)),
                'has_intent': 'intent' in data if isinstance(data, dict) else False
            }
        
        return features
    
    def _build_context_info(self, modality_inputs: Dict[ModalityType, List[ModalityInput]]) -> Dict[str, Any]:
        """
        构建上下文信息
        
        Args:
            modality_inputs: 模态输入
            
        Returns:
            上下文信息
        """
        context = {
            'active_modalities': list(modality_inputs.keys()),
            'total_inputs': sum(len(inputs) for inputs in modality_inputs.values()),
            'time_span': 0.0,
            'dominant_modality': None
        }
        
        # 计算时间跨度
        all_timestamps = []
        for inputs in modality_inputs.values():
            all_timestamps.extend([inp.timestamp for inp in inputs])
        
        if all_timestamps:
            context['time_span'] = max(all_timestamps) - min(all_timestamps)
        
        # 确定主导模态
        modality_counts = {mt: len(inputs) for mt, inputs in modality_inputs.items()}
        if modality_counts:
            context['dominant_modality'] = max(modality_counts.items(), key=lambda x: x[1])[0].value
        
        return context
    
    def set_modality_weights(self, weights: Dict[ModalityType, float]):
        """
        设置模态权重
        
        Args:
            weights: 权重字典
        """
        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            self.modality_weights.update({k: v/total_weight for k, v in weights.items()})
            self.logger.info(f"模态权重已更新: {self.modality_weights}")
    
    def add_fusion_callback(self, callback: Callable[[FusionResult], None]):
        """
        添加融合结果回调
        
        Args:
            callback: 回调函数
        """
        self.fusion_callbacks.append(callback)
        self.logger.debug("添加融合回调函数")
    
    def remove_fusion_callback(self, callback: Callable[[FusionResult], None]):
        """
        移除融合结果回调
        
        Args:
            callback: 回调函数
        """
        if callback in self.fusion_callbacks:
            self.fusion_callbacks.remove(callback)
            self.logger.debug("移除融合回调函数")
    
    def get_fusion_status(self) -> Dict[str, Any]:
        """
        获取融合引擎状态
        
        Returns:
            状态信息
        """
        with self.cache_lock:
            cache_sizes = {mt.value: len(inputs) for mt, inputs in self.temporal_cache.items()}
        
        return {
            'is_running': self.is_running,
            'fusion_strategy': self.fusion_strategy,
            'temporal_window': self.temporal_window,
            'modality_weights': self.modality_weights.copy(),
            'cache_sizes': cache_sizes,
            'callback_count': len(self.fusion_callbacks)
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._stop_fusion_thread()