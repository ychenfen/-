"""
知识库模块
基于向量数据库实现教育知识检索和管理
"""

import json
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import hashlib

class KnowledgeBase:
    def __init__(self, 
                 kb_path: str = "./knowledge_base",
                 embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 collection_name: str = "educational_knowledge"):
        """
        初始化知识库
        
        Args:
            kb_path: 知识库存储路径
            embedding_model: 嵌入模型名称
            collection_name: 集合名称
        """
        self.logger = logging.getLogger(__name__)
        self.kb_path = kb_path
        self.collection_name = collection_name
        
        # 创建知识库目录
        os.makedirs(kb_path, exist_ok=True)
        
        try:
            # 初始化嵌入模型
            self.embedding_model = SentenceTransformer(embedding_model)
            self.logger.info(f"嵌入模型加载成功: {embedding_model}")
            
            # 初始化ChromaDB
            self.client = chromadb.PersistentClient(
                path=kb_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Educational knowledge base"}
            )
            
            self.logger.info(f"知识库初始化成功: {kb_path}")
            
        except Exception as e:
            self.logger.error(f"知识库初始化失败: {e}")
            raise
    
    def add_knowledge(self, 
                     content: str, 
                     title: str = "",
                     subject: str = "general",
                     difficulty: str = "medium",
                     keywords: List[str] = None,
                     metadata: Dict[str, Any] = None) -> bool:
        """
        添加知识条目
        
        Args:
            content: 知识内容
            title: 标题
            subject: 学科分类
            difficulty: 难度级别
            keywords: 关键词列表
            metadata: 额外元数据
            
        Returns:
            是否添加成功
        """
        try:
            # 生成唯一ID
            knowledge_id = self._generate_id(content, title)
            
            # 生成嵌入向量
            embedding = self.embedding_model.encode(content).tolist()
            
            # 构建元数据
            item_metadata = {
                "title": title,
                "subject": subject,
                "difficulty": difficulty,
                "keywords": keywords or [],
                "content_length": len(content),
                "timestamp": self._get_timestamp()
            }
            
            if metadata:
                item_metadata.update(metadata)
            
            # 添加到集合
            self.collection.add(
                ids=[knowledge_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[item_metadata]
            )
            
            self.logger.debug(f"知识条目添加成功: {title}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加知识条目失败: {e}")
            return False
    
    def search_knowledge(self, 
                        query: str, 
                        n_results: int = 5,
                        subject_filter: str = None,
                        difficulty_filter: str = None,
                        min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """
        搜索相关知识
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            subject_filter: 学科过滤
            difficulty_filter: 难度过滤
            min_similarity: 最小相似度阈值
            
        Returns:
            搜索结果列表
        """
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # 构建过滤条件
            where_filter = {}
            if subject_filter:
                where_filter["subject"] = subject_filter
            if difficulty_filter:
                where_filter["difficulty"] = difficulty_filter
            
            # 执行搜索
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results
            }
            
            if where_filter:
                search_params["where"] = where_filter
            
            results = self.collection.query(**search_params)
            
            # 处理搜索结果
            knowledge_results = []
            for i in range(len(results['ids'][0])):
                # 计算相似度（ChromaDB使用距离，需要转换）
                distance = results['distances'][0][i]
                similarity = max(0, 1 - distance)  # 简单的距离转相似度
                
                if similarity >= min_similarity:
                    result_item = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity': similarity
                    }
                    knowledge_results.append(result_item)
            
            self.logger.debug(f"搜索到 {len(knowledge_results)} 条相关知识")
            return knowledge_results
            
        except Exception as e:
            self.logger.error(f"知识搜索失败: {e}")
            return []
    
    def get_subject_knowledge(self, subject: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取特定学科的知识
        
        Args:
            subject: 学科名称
            limit: 限制数量
            
        Returns:
            学科知识列表
        """
        try:
            results = self.collection.get(
                where={"subject": subject},
                limit=limit
            )
            
            knowledge_list = []
            for i in range(len(results['ids'])):
                item = {
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                }
                knowledge_list.append(item)
            
            return knowledge_list
            
        except Exception as e:
            self.logger.error(f"获取学科知识失败: {e}")
            return []
    
    def update_knowledge(self, knowledge_id: str, 
                        content: str = None,
                        metadata: Dict[str, Any] = None) -> bool:
        """
        更新知识条目
        
        Args:
            knowledge_id: 知识ID
            content: 新内容
            metadata: 新元数据
            
        Returns:
            是否更新成功
        """
        try:
            update_data = {}
            
            if content:
                # 重新生成嵌入
                embedding = self.embedding_model.encode(content).tolist()
                update_data['embeddings'] = [embedding]
                update_data['documents'] = [content]
            
            if metadata:
                update_data['metadatas'] = [metadata]
            
            if update_data:
                self.collection.update(
                    ids=[knowledge_id],
                    **update_data
                )
                
                self.logger.debug(f"知识条目更新成功: {knowledge_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"更新知识条目失败: {e}")
            return False
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        """
        删除知识条目
        
        Args:
            knowledge_id: 知识ID
            
        Returns:
            是否删除成功
        """
        try:
            self.collection.delete(ids=[knowledge_id])
            self.logger.debug(f"知识条目删除成功: {knowledge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除知识条目失败: {e}")
            return False
    
    def load_knowledge_from_file(self, file_path: str, 
                                subject: str = "general",
                                difficulty: str = "medium") -> int:
        """
        从文件加载知识
        
        Args:
            file_path: 文件路径
            subject: 学科分类
            difficulty: 难度级别
            
        Returns:
            成功加载的条目数量
        """
        try:
            success_count = 0
            
            if file_path.endswith('.json'):
                success_count = self._load_from_json(file_path, subject, difficulty)
            elif file_path.endswith('.txt'):
                success_count = self._load_from_text(file_path, subject, difficulty)
            else:
                self.logger.error(f"不支持的文件格式: {file_path}")
                return 0
            
            self.logger.info(f"从文件加载知识完成: {success_count} 条")
            return success_count
            
        except Exception as e:
            self.logger.error(f"从文件加载知识失败: {e}")
            return 0
    
    def _load_from_json(self, file_path: str, subject: str, difficulty: str) -> int:
        """
        从JSON文件加载知识
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        success_count = 0
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'content' in item:
                    if self.add_knowledge(
                        content=item['content'],
                        title=item.get('title', ''),
                        subject=item.get('subject', subject),
                        difficulty=item.get('difficulty', difficulty),
                        keywords=item.get('keywords', []),
                        metadata=item.get('metadata', {})
                    ):
                        success_count += 1
        
        return success_count
    
    def _load_from_text(self, file_path: str, subject: str, difficulty: str) -> int:
        """
        从文本文件加载知识
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        success_count = 0
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) > 50:  # 过滤太短的段落
                if self.add_knowledge(
                    content=paragraph,
                    title=f"段落_{i+1}",
                    subject=subject,
                    difficulty=difficulty
                ):
                    success_count += 1
        
        return success_count
    
    def export_knowledge(self, output_path: str, subject: str = None) -> bool:
        """
        导出知识库
        
        Args:
            output_path: 输出文件路径
            subject: 要导出的学科（None表示全部）
            
        Returns:
            是否导出成功
        """
        try:
            # 获取知识条目
            if subject:
                results = self.collection.get(where={"subject": subject})
            else:
                results = self.collection.get()
            
            # 构建导出数据
            export_data = []
            for i in range(len(results['ids'])):
                item = {
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                }
                export_data.append(item)
            
            # 保存到文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"知识库导出成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出知识库失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            all_items = self.collection.get()
            total_count = len(all_items['ids'])
            
            # 统计各学科数量
            subject_counts = {}
            difficulty_counts = {}
            
            for metadata in all_items['metadatas']:
                subject = metadata.get('subject', 'unknown')
                difficulty = metadata.get('difficulty', 'unknown')
                
                subject_counts[subject] = subject_counts.get(subject, 0) + 1
                difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
            
            statistics = {
                'total_items': total_count,
                'subjects': subject_counts,
                'difficulties': difficulty_counts,
                'collection_name': self.collection_name,
                'kb_path': self.kb_path
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def search_by_keywords(self, keywords: List[str], 
                          match_all: bool = False) -> List[Dict[str, Any]]:
        """
        根据关键词搜索
        
        Args:
            keywords: 关键词列表
            match_all: 是否需要匹配所有关键词
            
        Returns:
            搜索结果
        """
        try:
            results = []
            all_items = self.collection.get()
            
            for i, metadata in enumerate(all_items['metadatas']):
                item_keywords = metadata.get('keywords', [])
                
                if match_all:
                    # 必须包含所有关键词
                    if all(kw in item_keywords for kw in keywords):
                        results.append({
                            'id': all_items['ids'][i],
                            'content': all_items['documents'][i],
                            'metadata': metadata
                        })
                else:
                    # 包含任一关键词即可
                    if any(kw in item_keywords for kw in keywords):
                        results.append({
                            'id': all_items['ids'][i],
                            'content': all_items['documents'][i],
                            'metadata': metadata
                        })
            
            self.logger.debug(f"关键词搜索结果: {len(results)} 条")
            return results
            
        except Exception as e:
            self.logger.error(f"关键词搜索失败: {e}")
            return []
    
    def _generate_id(self, content: str, title: str = "") -> str:
        """
        生成唯一ID
        
        Args:
            content: 内容
            title: 标题
            
        Returns:
            唯一ID
        """
        text = f"{title}_{content}"
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_timestamp(self) -> str:
        """
        获取当前时间戳
        
        Returns:
            时间戳字符串
        """
        import datetime
        return datetime.datetime.now().isoformat()
    
    def clear_all_knowledge(self) -> bool:
        """
        清空所有知识
        
        Returns:
            是否成功
        """
        try:
            # 删除集合
            self.client.delete_collection(self.collection_name)
            
            # 重新创建集合
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Educational knowledge base"}
            )
            
            self.logger.info("知识库已清空")
            return True
            
        except Exception as e:
            self.logger.error(f"清空知识库失败: {e}")
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        # ChromaDB会自动持久化，无需特殊清理
        pass