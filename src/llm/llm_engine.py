"""
LLM推理引擎
基于transformers实现本地大语言模型推理
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
import onnxruntime as ort
from typing import Dict, List, Optional, Any, Tuple
import logging
import json
import threading
import queue
import time

class LLMEngine:
    def __init__(self, 
                 model_name: str = "Qwen/Qwen1.5-1.8B-Chat",
                 device: str = "cpu",
                 use_onnx: bool = False,
                 max_length: int = 2048):
        """
        初始化LLM推理引擎
        
        Args:
            model_name: 模型名称或路径
            device: 运行设备 ("cpu", "cuda")
            use_onnx: 是否使用ONNX优化
            max_length: 最大序列长度
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.device = device
        self.use_onnx = use_onnx
        self.max_length = max_length
        
        # 模型和分词器
        self.tokenizer = None
        self.model = None
        self.ort_session = None
        
        # 生成配置
        self.generation_config = GenerationConfig(
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.8,
            top_k=50,
            repetition_penalty=1.1,
            do_sample=True,
            pad_token_id=151643,  # Qwen的pad_token_id
            eos_token_id=151643
        )
        
        # 推理队列和线程管理
        self.inference_queue = queue.Queue()
        self.inference_thread = None
        self.is_processing = False
        
        # 对话历史管理
        self.conversation_history = []
        self.max_history_length = 10
        
        try:
            self._initialize_model()
            self.logger.info(f"LLM引擎初始化成功: {model_name}")
        except Exception as e:
            self.logger.error(f"LLM引擎初始化失败: {e}")
            raise
    
    def _initialize_model(self):
        """
        初始化模型和分词器
        """
        # 加载分词器
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            padding_side='left'
        )
        
        # 设置pad_token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        if self.use_onnx:
            # 使用ONNX Runtime
            self._load_onnx_model()
        else:
            # 使用PyTorch模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            self.model.eval()
    
    def _load_onnx_model(self):
        """
        加载ONNX优化模型
        """
        try:
            # 这里假设已经有转换好的ONNX模型
            onnx_model_path = f"{self.model_name.replace('/', '_')}.onnx"
            
            providers = ['CPUExecutionProvider']
            if self.device == "cuda" and 'CUDAExecutionProvider' in ort.get_available_providers():
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            self.ort_session = ort.InferenceSession(onnx_model_path, providers=providers)
            self.logger.info("ONNX模型加载成功")
            
        except Exception as e:
            self.logger.warning(f"ONNX模型加载失败，回退到PyTorch: {e}")
            self.use_onnx = False
            self._initialize_model()
    
    def generate_response(self, prompt: str, system_prompt: str = None, 
                         use_history: bool = True) -> Dict[str, Any]:
        """
        生成回复
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            use_history: 是否使用对话历史
            
        Returns:
            生成结果字典
        """
        try:
            # 构建完整的输入
            full_prompt = self._build_prompt(prompt, system_prompt, use_history)
            
            # 执行推理
            if self.use_onnx:
                response = self._generate_with_onnx(full_prompt)
            else:
                response = self._generate_with_pytorch(full_prompt)
            
            # 更新对话历史
            if use_history:
                self._update_conversation_history(prompt, response['text'])
            
            return response
            
        except Exception as e:
            self.logger.error(f"生成回复失败: {e}")
            return {
                'text': '抱歉，我现在无法回答这个问题。',
                'confidence': 0.0,
                'tokens_used': 0,
                'generation_time': 0.0
            }
    
    def _build_prompt(self, user_input: str, system_prompt: str = None, 
                      use_history: bool = True) -> str:
        """
        构建完整的提示词
        
        Args:
            user_input: 用户输入
            system_prompt: 系统提示词
            use_history: 是否使用历史
            
        Returns:
            完整的提示词
        """
        # 默认系统提示词（教育助手角色）
        if system_prompt is None:
            system_prompt = \"\"\"你是一个智能教育助手机器人，专门帮助学生学习。你的任务是：
1. 回答学生的学习问题，提供清晰易懂的解释
2. 鼓励学生思考，引导他们找到答案
3. 保持耐心和友好的态度
4. 根据学生的理解水平调整解释的难度
5. 提供相关的学习建议和练习

请用简洁、友好、鼓励的语调回答问题。\"\"\"
        
        # 构建对话格式
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话
        if use_history and self.conversation_history:
            for history_item in self.conversation_history[-self.max_history_length:]:
                messages.append({"role": "user", "content": history_item["user"]})
                messages.append({"role": "assistant", "content": history_item["assistant"]})
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        # 使用分词器的chat template
        try:
            full_prompt = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
        except:
            # 如果chat template不可用，使用简单格式
            full_prompt = f"{system_prompt}\n\nUser: {user_input}\nAssistant: "
        
        return full_prompt
    
    def _generate_with_pytorch(self, prompt: str) -> Dict[str, Any]:
        """
        使用PyTorch模型生成回复
        
        Args:
            prompt: 输入提示词
            
        Returns:
            生成结果
        """
        start_time = time.time()
        
        # 编码输入
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length - self.generation_config.max_new_tokens
        ).to(self.device)
        
        # 生成回复
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                generation_config=self.generation_config,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        # 解码输出
        generated_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        response_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        generation_time = time.time() - start_time
        
        return {
            'text': response_text.strip(),
            'confidence': 0.8,  # PyTorch模式下的估计置信度
            'tokens_used': len(generated_tokens),
            'generation_time': generation_time
        }
    
    def _generate_with_onnx(self, prompt: str) -> Dict[str, Any]:
        """
        使用ONNX模型生成回复
        
        Args:
            prompt: 输入提示词
            
        Returns:
            生成结果
        """
        start_time = time.time()
        
        # 编码输入
        inputs = self.tokenizer(
            prompt,
            return_tensors="np",
            truncation=True,
            max_length=self.max_length - self.generation_config.max_new_tokens
        )
        
        # ONNX推理
        ort_inputs = {self.ort_session.get_inputs()[0].name: inputs['input_ids']}
        outputs = self.ort_session.run(None, ort_inputs)
        
        # 这里需要实现ONNX的生成逻辑
        # 简化版本，实际需要实现完整的生成循环
        response_text = "ONNX推理功能正在开发中"
        
        generation_time = time.time() - start_time
        
        return {
            'text': response_text,
            'confidence': 0.7,
            'tokens_used': 0,
            'generation_time': generation_time
        }
    
    def generate_educational_response(self, question: str, subject: str = "general", 
                                    difficulty_level: str = "medium") -> Dict[str, Any]:
        """
        生成教育相关回复
        
        Args:
            question: 学生问题
            subject: 学科领域 ("math", "chinese", "english", "science", "general")
            difficulty_level: 难度级别 ("easy", "medium", "hard")
            
        Returns:
            教育回复结果
        """
        # 构建教育专用系统提示词
        subject_prompts = {
            "math": "你是一个数学老师，擅长用简单易懂的方式解释数学概念和解题方法。",
            "chinese": "你是一个语文老师，擅长诗词文学和语言文字的教学。",
            "english": "你是一个英语老师，擅长英语语法、词汇和口语教学。",
            "science": "你是一个科学老师，擅长用生动有趣的方式解释自然科学现象。",
            "general": "你是一个全科教师，能够回答各种学科的问题。"
        }
        
        difficulty_instructions = {
            "easy": "请用最简单的语言解释，适合初学者理解。",
            "medium": "请提供适中难度的解释，包含一些具体例子。",
            "hard": "请提供深入详细的解释，可以包含高级概念。"
        }
        
        system_prompt = f\"\"\"{subject_prompts.get(subject, subject_prompts["general"])}
{difficulty_instructions.get(difficulty_level, difficulty_instructions["medium"])}

请遵循以下教学原则：
1. 先理解学生的问题，确保回答准确
2. 用循序渐进的方式解释
3. 提供具体的例子和类比
4. 鼓励学生思考和提问
5. 如果是习题，提供解题思路而不是直接答案\"\"\"
        
        return self.generate_response(question, system_prompt, use_history=True)
    
    def ask_follow_up_question(self, topic: str) -> str:
        """
        生成后续问题
        
        Args:
            topic: 话题内容
            
        Returns:
            后续问题
        """
        prompt = f"基于刚才关于'{topic}'的讨论，请提出一个相关的思考问题来帮助学生深入理解。"
        
        system_prompt = \"\"\"你是一个善于提问的老师。请生成一个有启发性的问题，帮助学生：
1. 深入思考刚才讨论的内容
2. 将知识与实际生活联系
3. 发现新的学习兴趣点
请直接给出问题，不需要额外解释。\"\"\"
        
        response = self.generate_response(prompt, system_prompt, use_history=False)
        return response['text']
    
    def _update_conversation_history(self, user_input: str, assistant_response: str):
        """
        更新对话历史
        
        Args:
            user_input: 用户输入
            assistant_response: 助手回复
        """
        self.conversation_history.append({
            "user": user_input,
            "assistant": assistant_response,
            "timestamp": time.time()
        })
        
        # 保持历史长度限制
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def clear_conversation_history(self):
        """
        清空对话历史
        """
        self.conversation_history = []
        self.logger.info("对话历史已清空")
    
    def get_conversation_summary(self) -> str:
        """
        获取对话摘要
        
        Returns:
            对话摘要文本
        """
        if not self.conversation_history:
            return "暂无对话历史"
        
        # 构建摘要提示词
        history_text = ""
        for item in self.conversation_history[-5:]:  # 最近5轮对话
            history_text += f"学生: {item['user']}\n老师: {item['assistant']}\n\n"
        
        prompt = f"请为以下师生对话提供一个简洁的摘要：\n\n{history_text}"
        
        system_prompt = "请简洁地总结对话内容，重点关注讨论的主题和学生的学习进展。"
        
        response = self.generate_response(prompt, system_prompt, use_history=False)
        return response['text']
    
    def evaluate_response_quality(self, question: str, response: str) -> Dict[str, float]:
        """
        评估回复质量
        
        Args:
            question: 原问题
            response: 生成的回复
            
        Returns:
            质量评估结果
        """
        # 简化的质量评估算法
        quality_scores = {
            'relevance': 0.8,      # 相关性
            'clarity': 0.8,        # 清晰度
            'completeness': 0.7,   # 完整性
            'educational_value': 0.8  # 教育价值
        }
        
        # 基于长度和关键词的简单评估
        if len(response) < 20:
            quality_scores['completeness'] *= 0.5
        
        if len(response) > 500:
            quality_scores['clarity'] *= 0.8
        
        # 检查是否包含教育关键词
        educational_keywords = ['学习', '理解', '例子', '思考', '练习', '原理', '方法']
        keyword_count = sum(1 for keyword in educational_keywords if keyword in response)
        quality_scores['educational_value'] = min(1.0, keyword_count / 3)
        
        return quality_scores
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            'model_name': self.model_name,
            'device': self.device,
            'use_onnx': self.use_onnx,
            'max_length': self.max_length,
            'conversation_length': len(self.conversation_history),
            'generation_config': {
                'max_new_tokens': self.generation_config.max_new_tokens,
                'temperature': self.generation_config.temperature,
                'top_p': self.generation_config.top_p
            }
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        # 清理资源
        if self.model:
            del self.model
        if self.ort_session:
            del self.ort_session
        torch.cuda.empty_cache() if torch.cuda.is_available() else None