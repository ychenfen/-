"""
对话管理模块
管理多轮对话状态、上下文和教学策略
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

from .llm_engine import LLMEngine
from .knowledge_base import KnowledgeBase

class DialogueState(Enum):
    """对话状态枚举"""
    IDLE = "idle"                    # 空闲状态
    GREETING = "greeting"            # 问候状态  
    QUESTIONING = "questioning"      # 提问状态
    EXPLAINING = "explaining"        # 解释状态
    ENCOURAGING = "encouraging"      # 鼓励状态
    SUMMARIZING = "summarizing"      # 总结状态
    ENDING = "ending"               # 结束状态

class DialogueManager:
    def __init__(self, 
                 llm_engine: LLMEngine,
                 knowledge_base: KnowledgeBase,
                 max_turns: int = 20,
                 context_window: int = 5):
        """
        初始化对话管理器
        
        Args:
            llm_engine: LLM推理引擎
            knowledge_base: 知识库
            max_turns: 最大对话轮数
            context_window: 上下文窗口大小
        """
        self.logger = logging.getLogger(__name__)
        self.llm_engine = llm_engine
        self.knowledge_base = knowledge_base
        self.max_turns = max_turns
        self.context_window = context_window
        
        # 对话状态管理
        self.current_state = DialogueState.IDLE
        self.dialogue_history = []
        self.current_topic = None
        self.user_profile = {}
        self.session_start_time = None
        
        # 教学策略
        self.teaching_strategies = {
            'beginner': {
                'explanation_style': 'simple',
                'use_examples': True,
                'encouragement_frequency': 'high'
            },
            'intermediate': {
                'explanation_style': 'detailed',
                'use_examples': True,
                'encouragement_frequency': 'medium'
            },
            'advanced': {
                'explanation_style': 'comprehensive',
                'use_examples': False,
                'encouragement_frequency': 'low'
            }
        }
        
        # 状态转换规则
        self.state_transitions = {
            DialogueState.IDLE: [DialogueState.GREETING],
            DialogueState.GREETING: [DialogueState.QUESTIONING, DialogueState.EXPLAINING],
            DialogueState.QUESTIONING: [DialogueState.EXPLAINING, DialogueState.ENCOURAGING],
            DialogueState.EXPLAINING: [DialogueState.QUESTIONING, DialogueState.SUMMARIZING],
            DialogueState.ENCOURAGING: [DialogueState.QUESTIONING, DialogueState.EXPLAINING],
            DialogueState.SUMMARIZING: [DialogueState.QUESTIONING, DialogueState.ENDING],
            DialogueState.ENDING: [DialogueState.IDLE]
        }
        
        self.logger.info("对话管理器初始化成功")
    
    def start_session(self, user_name: str = None, user_level: str = "intermediate") -> Dict[str, Any]:
        """
        开始对话会话
        
        Args:
            user_name: 用户姓名
            user_level: 用户水平
            
        Returns:
            会话开始信息
        """
        self.session_start_time = time.time()
        self.current_state = DialogueState.GREETING
        self.dialogue_history = []
        
        # 初始化用户画像
        self.user_profile = {
            'name': user_name or "同学",
            'level': user_level,
            'interests': [],
            'learning_progress': {},
            'interaction_count': 0,
            'correct_answers': 0,
            'questions_asked': 0
        }
        
        # 生成问候语
        greeting_response = self._generate_greeting()
        
        # 记录对话
        self._add_to_history("system", greeting_response['text'], DialogueState.GREETING)
        
        self.logger.info(f"对话会话开始，用户: {self.user_profile['name']}")
        
        return {
            'response': greeting_response,
            'state': self.current_state.value,
            'session_id': self._generate_session_id()
        }
    
    def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            context: 额外上下文信息
            
        Returns:
            处理结果
        """
        try:
            # 更新用户画像
            self._update_user_profile(user_input)
            
            # 分析用户意图
            intent = self._analyze_intent(user_input)
            
            # 检索相关知识
            relevant_knowledge = self._retrieve_knowledge(user_input, intent)
            
            # 生成回复
            response = self._generate_response(user_input, intent, relevant_knowledge, context)
            
            # 更新对话状态
            self._update_dialogue_state(intent, response)
            
            # 记录对话历史
            self._add_to_history("user", user_input, self.current_state)
            self._add_to_history("assistant", response['text'], self.current_state)
            
            # 检查是否需要状态转换
            next_action = self._decide_next_action(intent, response)
            
            result = {
                'response': response,
                'state': self.current_state.value,
                'intent': intent,
                'next_action': next_action,
                'relevant_knowledge': relevant_knowledge,
                'user_profile': self.user_profile.copy()
            }
            
            self.logger.debug(f"处理用户输入完成，意图: {intent}")
            return result
            
        except Exception as e:
            self.logger.error(f"处理用户输入失败: {e}")
            return {
                'response': {'text': '抱歉，我现在有点困惑，请重新说一遍好吗？'},
                'state': self.current_state.value,
                'intent': 'unknown',
                'error': str(e)
            }
    
    def _generate_greeting(self) -> Dict[str, Any]:
        """
        生成问候语
        
        Returns:
            问候语回复
        """
        user_name = self.user_profile['name']
        greeting_prompts = [
            f"你好{user_name}！我是你的智能学习助手，很高兴见到你！",
            f"嗨{user_name}！准备好开始今天的学习了吗？",
            f"欢迎{user_name}！有什么学习问题想要讨论的吗？"
        ]
        
        import random
        greeting_text = random.choice(greeting_prompts)
        
        return {
            'text': greeting_text,
            'confidence': 1.0,
            'tokens_used': 0,
            'generation_time': 0.0
        }
    
    def _analyze_intent(self, user_input: str) -> str:
        """
        分析用户意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            意图类型
        """
        user_input_lower = user_input.lower()
        
        # 简化的意图识别规则
        if any(word in user_input_lower for word in ['你好', '嗨', '问候']):
            return 'greeting'
        elif any(word in user_input_lower for word in ['？', '?', '什么', '如何', '怎么', '为什么']):
            return 'question'
        elif any(word in user_input_lower for word in ['谢谢', '感谢', '明白了', '懂了']):
            return 'acknowledgment'
        elif any(word in user_input_lower for word in ['再见', '拜拜', '结束']):
            return 'goodbye'
        elif any(word in user_input_lower for word in ['不懂', '不明白', '解释']):
            return 'request_explanation'
        elif any(word in user_input_lower for word in ['练习', '题目', '测试']):
            return 'request_practice'
        else:
            return 'general_inquiry'
    
    def _retrieve_knowledge(self, user_input: str, intent: str) -> List[Dict[str, Any]]:
        """
        检索相关知识
        
        Args:
            user_input: 用户输入
            intent: 用户意图
            
        Returns:
            相关知识列表
        """
        if intent in ['question', 'request_explanation', 'general_inquiry']:
            # 根据当前话题和用户水平过滤
            current_subject = self.current_topic.get('subject', None) if self.current_topic else None
            user_level = self.user_profile.get('level', 'intermediate')
            
            # 映射用户水平到难度
            difficulty_mapping = {
                'beginner': 'easy',
                'intermediate': 'medium', 
                'advanced': 'hard'
            }
            difficulty = difficulty_mapping.get(user_level, 'medium')
            
            return self.knowledge_base.search_knowledge(
                query=user_input,
                n_results=3,
                subject_filter=current_subject,
                difficulty_filter=difficulty,
                min_similarity=0.3
            )
        
        return []
    
    def _generate_response(self, user_input: str, intent: str, 
                          relevant_knowledge: List[Dict], context: Dict = None) -> Dict[str, Any]:
        """
        生成回复
        
        Args:
            user_input: 用户输入
            intent: 用户意图
            relevant_knowledge: 相关知识
            context: 额外上下文
            
        Returns:
            生成的回复
        """
        # 根据意图选择合适的生成策略
        if intent == 'greeting':
            return {'text': f"你好！我是你的学习助手，有什么可以帮助你的吗？"}
        
        elif intent == 'goodbye':
            summary = self._generate_session_summary()
            return {'text': f"再见{self.user_profile['name']}！{summary}"}
        
        elif intent == 'acknowledgment':
            encouragement = self._generate_encouragement()
            return {'text': encouragement}
        
        else:
            # 构建增强的提示词
            enhanced_prompt = self._build_enhanced_prompt(user_input, relevant_knowledge, context)
            
            # 根据用户水平选择生成参数
            user_level = self.user_profile.get('level', 'intermediate')
            
            return self.llm_engine.generate_educational_response(
                question=enhanced_prompt,
                subject=self.current_topic.get('subject', 'general') if self.current_topic else 'general',
                difficulty_level=user_level
            )
    
    def _build_enhanced_prompt(self, user_input: str, relevant_knowledge: List[Dict], 
                             context: Dict = None) -> str:
        """
        构建增强的提示词
        
        Args:
            user_input: 用户输入
            relevant_knowledge: 相关知识
            context: 上下文
            
        Returns:
            增强的提示词
        """
        prompt_parts = [user_input]
        
        # 添加相关知识
        if relevant_knowledge:
            prompt_parts.append("\\n参考知识：")
            for knowledge in relevant_knowledge[:2]:  # 最多使用2条知识
                prompt_parts.append(f"- {knowledge['content'][:200]}...")
        
        # 添加对话历史上下文
        if self.dialogue_history:
            recent_history = self.dialogue_history[-self.context_window:]
            context_text = []
            for item in recent_history:
                if item['role'] == 'user':
                    context_text.append(f"学生之前问过：{item['content']}")
            
            if context_text:
                prompt_parts.append("\\n对话背景：")
                prompt_parts.extend(context_text)
        
        # 添加用户画像信息
        user_info = f"\\n学生信息：姓名-{self.user_profile['name']}，水平-{self.user_profile['level']}"
        prompt_parts.append(user_info)
        
        return "\\n".join(prompt_parts)
    
    def _update_dialogue_state(self, intent: str, response: Dict[str, Any]):
        """
        更新对话状态
        
        Args:
            intent: 用户意图
            response: 助手回复
        """
        # 基于意图和当前状态决定下一个状态
        if intent == 'question' and self.current_state != DialogueState.QUESTIONING:
            if DialogueState.QUESTIONING in self.state_transitions.get(self.current_state, []):
                self.current_state = DialogueState.QUESTIONING
        
        elif intent == 'request_explanation':
            if DialogueState.EXPLAINING in self.state_transitions.get(self.current_state, []):
                self.current_state = DialogueState.EXPLAINING
        
        elif intent == 'acknowledgment':
            if DialogueState.ENCOURAGING in self.state_transitions.get(self.current_state, []):
                self.current_state = DialogueState.ENCOURAGING
        
        elif intent == 'goodbye':
            self.current_state = DialogueState.ENDING
    
    def _update_user_profile(self, user_input: str):
        """
        更新用户画像
        
        Args:
            user_input: 用户输入
        """
        self.user_profile['interaction_count'] += 1
        
        # 分析用户水平（基于问题复杂度）
        if len(user_input) > 100 and any(word in user_input for word in ['原理', '机制', '深入']):
            if self.user_profile['level'] == 'beginner':
                self.user_profile['level'] = 'intermediate'
        
        # 更新兴趣话题
        if self.current_topic:
            subject = self.current_topic.get('subject')
            if subject and subject not in self.user_profile['interests']:
                self.user_profile['interests'].append(subject)
    
    def _decide_next_action(self, intent: str, response: Dict[str, Any]) -> str:
        """
        决定下一步行动
        
        Args:
            intent: 用户意图
            response: 助手回复
            
        Returns:
            下一步行动
        """
        # 检查是否需要提问
        if self.current_state == DialogueState.EXPLAINING:
            return 'ask_follow_up'
        
        # 检查是否需要鼓励
        if self.user_profile['interaction_count'] % 3 == 0:
            return 'provide_encouragement'
        
        # 检查是否需要总结
        if len(self.dialogue_history) > 10:
            return 'summarize_progress'
        
        return 'continue_conversation'
    
    def _generate_encouragement(self) -> str:
        """
        生成鼓励语
        
        Returns:
            鼓励文本
        """
        encouragements = [
            "很好！你的思考很有深度。",
            "不错！继续保持这种学习态度。",
            "优秀！你提出了一个很好的问题。",
            "棒！你对这个知识点掌握得不错。"
        ]
        
        import random
        return random.choice(encouragements)
    
    def _generate_session_summary(self) -> str:
        """
        生成会话总结
        
        Returns:
            会话总结
        """
        if not self.dialogue_history:
            return "感谢你的学习时间！"
        
        interaction_count = self.user_profile['interaction_count']
        session_duration = time.time() - self.session_start_time if self.session_start_time else 0
        
        summary = f"今天我们聊了{interaction_count}轮，用时{session_duration/60:.1f}分钟。"
        
        if self.user_profile['interests']:
            topics = "、".join(self.user_profile['interests'])
            summary += f"主要讨论了{topics}相关内容。"
        
        summary += "继续努力学习哦！"
        
        return summary
    
    def _add_to_history(self, role: str, content: str, state: DialogueState):
        """
        添加到对话历史
        
        Args:
            role: 角色 ("user" 或 "assistant" 或 "system")
            content: 内容
            state: 对话状态
        """
        self.dialogue_history.append({
            'role': role,
            'content': content,
            'state': state.value,
            'timestamp': time.time()
        })
        
        # 保持历史长度限制
        if len(self.dialogue_history) > self.max_turns * 2:
            self.dialogue_history = self.dialogue_history[-self.max_turns * 2:]
    
    def _generate_session_id(self) -> str:
        """
        生成会话ID
        
        Returns:
            会话ID
        """
        import hashlib
        timestamp = str(time.time())
        user_name = self.user_profile.get('name', 'anonymous')
        session_data = f"{timestamp}_{user_name}"
        return hashlib.md5(session_data.encode()).hexdigest()[:8]
    
    def get_dialogue_state(self) -> Dict[str, Any]:
        """
        获取对话状态
        
        Returns:
            状态信息
        """
        return {
            'current_state': self.current_state.value,
            'dialogue_turns': len(self.dialogue_history),
            'current_topic': self.current_topic,
            'user_profile': self.user_profile.copy(),
            'session_duration': time.time() - self.session_start_time if self.session_start_time else 0
        }
    
    def set_topic(self, topic: str, subject: str = "general"):
        """
        设置当前话题
        
        Args:
            topic: 话题内容
            subject: 学科分类
        """
        self.current_topic = {
            'topic': topic,
            'subject': subject,
            'timestamp': time.time()
        }
        self.logger.info(f"设置话题: {topic} ({subject})")
    
    def end_session(self) -> Dict[str, Any]:
        """
        结束对话会话
        
        Returns:
            会话结束信息
        """
        summary = self._generate_session_summary()
        session_stats = {
            'duration': time.time() - self.session_start_time if self.session_start_time else 0,
            'total_turns': len(self.dialogue_history),
            'user_interactions': self.user_profile['interaction_count'],
            'topics_discussed': self.user_profile['interests'],
            'final_level': self.user_profile['level']
        }
        
        # 重置状态
        self.current_state = DialogueState.IDLE
        self.dialogue_history = []
        self.current_topic = None
        self.user_profile = {}
        self.session_start_time = None
        
        self.logger.info("对话会话结束")
        
        return {
            'summary': summary,
            'stats': session_stats
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.current_state != DialogueState.IDLE:
            self.end_session()