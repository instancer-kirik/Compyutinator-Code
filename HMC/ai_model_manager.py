import os
import subprocess
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from transformers import pipeline
import time
import psutil
import hashlib
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QProcess
from llama_cpp import Llama
import anthropic
import openai  # Add this import

from PyQt6.QtCore import QSettings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from string import punctuation
from heapq import nlargest
from collections import Counter
import re
from collections import deque
from typing import Optional
from HMC.context_manager import ContextManager
from HMC.ai_backend import create_ai_backend
from HMC.config.ai_config import AIConfig, ModelType
from typing import Dict, List, Optional, Deque
from collections import deque
import ast
import networkx as nx
import asyncio
import logging
from HMC.code_manager import CodeAnalyzer

# Define threshold

threshold = 0.5

class AIMemoryManager:
    def __init__(self, max_memories=100):
        self.code_memory = []
        self.project_memory = deque(maxlen=max_memories)
        self.conversation_history = deque(maxlen=max_memories)
        self.code_embeddings = {}
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def add_conversation(self, role: str, content: str):
        """Add conversation message"""
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })

    def get_conversation_context(self, n_messages: int = 5) -> List[Dict]:
        """Get recent conversation context"""
        return list(self.conversation_history)[-n_messages:]

    def add_memory(self, description, content, memory_type='code'):
        if memory_type == 'code':
            if description.startswith("File:"):
                file_path = description.split("File: ", 1)[1]
                description = f"File: {os.path.abspath(file_path)}"
            if content not in self.code_embeddings:
                self.code_embeddings[content] = self.get_code_embedding(content)
            if self.should_remember_code(content):
                self.code_memory.append((description, content))
        elif memory_type == 'project':
            self.project_memory.append((description, content))

    def should_remember_code(self, content):
        relevant_keywords = ['def ', 'class ', 'import ', 'from ', 'if __name__']
        return any(keyword in content for keyword in relevant_keywords)

    def add_project_info(self, info_type, content):
        self.project_memory.append((info_type, content))

    def get_memory(self, description, memory_type='code'):
        memory = self.code_memory if memory_type == 'code' else self.project_memory
        for desc, content in memory:
            if desc == description:
                return content
        return None

    def get_relevant_memories(self, query, top_n=3):
        all_memories = self.code_memory + list(self.project_memory)
        scored_memories = [(desc, content, self.relevance_score(query, content)) 
                           for desc, content in all_memories]
        sorted_memories = sorted(scored_memories, key=lambda x: x[2], reverse=True)
        logging.debug(f"Sorted memories (top {top_n}): {sorted_memories[:top_n]}")
        return [(f"File: {os.path.abspath(desc.split('File: ', 1)[1])}", content, score) if desc.startswith("File:") else (desc, content, score) for desc, content, score in sorted_memories[:top_n]]
        #wow
    def relevance_score(self, query, content):
        if self.is_code_content(content):
            return self.code_relevance_score(query, content)
        else:
            return self.nlp_relevance_score(query, content)

    def is_code_content(self, content):
        code_indicators = ['def ', 'class ', 'import ', 'from ', 'if __name__']
        return any(indicator in content for indicator in code_indicators)

    def code_relevance_score(self, query, content):
        query_words = set(re.findall(r'\w+', query.lower()))
        content_words = set(re.findall(r'\w+', content.lower()))
        return len(query_words.intersection(content_words))

    def nlp_relevance_score(self, query, content):
        tfidf_matrix = self.vectorizer.fit_transform([query, content])
        return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    def clear_memory(self, memory_type=None):
        if memory_type == 'code' or memory_type is None:
            self.code_memory = []
        if memory_type == 'project' or memory_type is None:
            self.project_memory.clear()

    def get_all_memories(self):
        return {'code': self.code_memory, 'project': list(self.project_memory)}

    def get_context_aware_completions(self, current_code, cursor_position):
        relevant_memories = self.get_relevant_memories(current_code, top_n=5)
        # Use relevant memories to generate completion suggestions
        # This is a placeholder for more sophisticated completion logic
        return [mem[1] for mem in relevant_memories]

class ModelLoadWorker(QThread):
    progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    finished = pyqtSignal(Llama)
    error = pyqtSignal(str)
    
    def __init__(self, repo_id, filename):
        super().__init__()
        self.repo_id = repo_id
        self.filename = filename

    def run(self):
        try:
            def progress_callback(bytes_downloaded, total_bytes):
                self.progress.emit(bytes_downloaded, total_bytes)

            model = Llama.from_pretrained(
                repo_id=self.repo_id,
                filename=self.filename,
                n_ctx=6000,
                progress_callback=progress_callback
            )
            self.finished.emit(model)
        except Exception as e:
            self.error.emit(str(e))

class GenerateWorker(QThread):
    finished = pyqtSignal(str, str)  # response, chat_type
    error = pyqtSignal(str, str)     # error message, chat_type
    partial_response = pyqtSignal(str, str)  # partial response, chat_type

    def __init__(self, backend, prompt: str, chat_type: str, max_tokens: int = 2000):
        super().__init__()
        self.backend = backend
        self.prompt = prompt
        self.chat_type = chat_type
        self.max_tokens = max_tokens
        self._is_running = True

    def run(self):
        try:
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            response = loop.run_until_complete(self._generate())
            
            if self._is_running:  # Check if cancelled
                self.finished.emit(response, self.chat_type)
                
        except Exception as e:
            self.error.emit(str(e), self.chat_type)
        finally:
            loop.close()

    async def _generate(self):
        try:
            async for chunk in self.backend.stream(
                self.prompt,
                lambda x: self.partial_response.emit(x, self.chat_type)
            ):
                if not self._is_running:  # Check for cancellation
                    break
            return ""  # Full response handled through streaming
        except Exception as e:
            logging.error(f"Generation error: {e}")
            raise

    def stop(self):
        """Cancel the generation"""
        self._is_running = False

class ModelManager(QObject):
    model_loading = pyqtSignal()
    model_loaded = pyqtSignal(str)
    model_error = pyqtSignal(str)
    model_download_progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    generation_finished = pyqtSignal(str, str)  # response, chat_type
    generation_error = pyqtSignal(str, str)  # error message, chat_type
    partial_response = pyqtSignal(str, str)  # partial response, chat_type
    memory_manager = AIMemoryManager()

    def __init__(self, cccore):
        super().__init__()
        self.cccore = cccore
        self.memory_manager = AIMemoryManager()
        # Initialize without context manager first
        self.context_manager = None
        self.current_config = None
        self.backends = {}
        self.active_workers = {}
        self.config = self.cccore.config_manager.get_ai_config()
        
    def setup_context_manager(self, context_manager):
        """Set up context manager after initialization"""
        self.context_manager = context_manager
    
    def load_model(self, config: AIConfig):
        try:
            backend = create_ai_backend(config)
            backend.setup_context(self.context_manager, self.memory_manager)
            self.backends[config.model_type] = backend
            self.current_config = config
            self.model_loaded.emit(f"{config.model_type.value}: {config.model_name}")
        except Exception as e:
            self.model_error.emit(str(e))

    async def generate(self, prompt: str, chat_type='local', **kwargs):
        try:
            model_type = ModelType.LOCAL if chat_type == 'local' else self.current_config.model_type
            backend = self.backends.get(model_type)
            
            if not backend:
                raise ValueError(f"No backend loaded for {model_type}")
                
            response = await backend.generate_with_context(prompt, **kwargs)
            self.generation_finished.emit(response, chat_type)
            
        except Exception as e:
            self.generation_error.emit(str(e), chat_type)

    async def process_tasks(self):
        """Process multiple model tasks in parallel"""
        while True:
            task = await self.task_queue.get()
            if task.type == 'generate':
                asyncio.create_task(self.generate_async(task))
            elif task.type == 'analyze':
                asyncio.create_task(self.analyze_code_async(task))

    def on_generation_finished(self, response, chat_type):
        self.generation_finished.emit(response, chat_type)

    def on_generation_error(self, error):
        logging.error(f"Generation error: {error}")
        self.generation_error.emit(str(error))

    def get_model_size(self, model_name=None):
        if model_name is None:
            model_name = self.current_local_model_name
        
        if model_name is None:
            logging.warning("No model specified and no current model loaded.")
            return 0
        
        model_path = os.path.join(self.models_dir, model_name)
        if not os.path.exists(model_path):
            logging.error(f"Model file not found: {model_path}")
            return 0
        
        return os.path.getsize(model_path)

    def change_model(self, model_type: ModelType, model_name: str):
        """Change model with proper config"""
        if model_type == ModelType.LOCAL:
            config = AIConfig.default_local()
            config.model_name = model_name
        elif model_type == ModelType.OPENAI:
            config = AIConfig.default_openai(self.config.get_openai_key())
            config.model_name = model_name
        elif model_type == ModelType.ANTHROPIC:
            config = AIConfig.default_anthropic(self.config.get_anthropic_key())
            config.model_name = model_name
            
        self.load_model(config)

    def get_model_type(self, model_name=None):
        if model_name is None:
            model_name = self.current_local_model_name or self.current_remote_model_name
        if model_name in ['Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ4_K_M.gguf','Llama-3.1-SuperNova-Lite-8.0B-OF32.EF32.IQ4_K_M']:
            return 'local'
        elif model_name in ['gpt-3.5-turbo', 'gpt-4','Claude-3-5-Sonnet-20240620']:
            return 'remote'
        else:
            raise ValueError(f"Unknown model: {model_name}")

    def on_local_model_loaded(self, model):
        self.local_model = model
        self.current_local_model_name = self.load_worker.filename.replace('.gguf', '')
        self.model_loaded.emit(f"Local: {self.current_local_model_name}")

    def on_model_error(self, error):
        self.model_error.emit(str(error))

    def on_local_model_load_error(self, error):
        logging.error(f"Error loading local model: {error}")
        logging.info(f"Falling back to static model: {self.static_model_name}")
        self.load_model('local', self.static_model_name)

class EnhancedMemoryManager:
    def __init__(self, max_memories=100):
        self.code_memory = []
        self.project_memory: Deque = deque(maxlen=max_memories)
        self.conversation_history: List[Dict] = []
        self.code_analyzer = CodeAnalyzer()
        
    async def add_memory(self, content: str, memory_type: str = 'code'):
        """Enhanced memory management without LangChain dependency"""
        if memory_type == 'code':
            # Analyze code before storing
            analysis = await self.code_analyzer.analyze_code(content)
            self.code_memory.append({
                'content': content,
                'analysis': analysis,
                'embedding': self.get_code_embedding(content)
            })
        else:
            self.project_memory.append({
                'content': content,
                'type': memory_type
            })

    def get_conversation_context(self, n_messages: int = 5) -> List[Dict]:
        """Get recent conversation context"""
        return self.conversation_history[-n_messages:] if self.conversation_history else []
