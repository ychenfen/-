"""
大语言模型模块
提供本地LLM推理、知识问答和对话管理功能
"""

from .llm_engine import LLMEngine
from .knowledge_base import KnowledgeBase
from .dialogue_manager import DialogueManager

__all__ = ['LLMEngine', 'KnowledgeBase', 'DialogueManager']