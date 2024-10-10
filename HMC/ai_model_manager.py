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

from PyQt6.QtCore import QSettings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from string import punctuation
from heapq import nlargest
from collections import Counter
import re
from collections import deque
# Define threshold

threshold = 0.5

class AIMemoryManager:
    def __init__(self, max_memories=100):
        self.code_memory = []
        self.project_memory = deque(maxlen=max_memories)
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def add_memory(self, description, content, memory_type='code'):
        if memory_type == 'code':
            if description.startswith("File:"):
                file_path = description.split("File: ", 1)[1]
                description = f"File: {os.path.abspath(file_path)}"
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
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    partial_response = pyqtSignal(str)  # New signal for partial responses

    def __init__(self, model, messages, max_tokens):
        super().__init__()
        self.model = model
        self.messages = messages
        self.max_tokens = max_tokens

    def run(self):
        try:
            logging.debug("Starting chat completion generation")
            response = self.model.create_chat_completion(
                messages=self.messages,
                max_tokens=self.max_tokens
            )
            for partial in response['choices'][0]['message']['content']:
                self.partial_response.emit(partial)
            logging.debug("Chat completion generated successfully")
            self.finished.emit(response['choices'][0]['message']['content'])
        except Exception as e:
            logging.error(f"Error during chat completion generation: {e}")
            self.error.emit(str(e))

class ModelManager(QObject):
    model_loading = pyqtSignal()
    model_loaded = pyqtSignal(str)
    model_error = pyqtSignal(str)
    model_download_progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    generation_finished = pyqtSignal(str)
    generation_error = pyqtSignal(str)
    partial_response = pyqtSignal(str)  # New signal for partial responses
    memory_manager = AIMemoryManager()
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.model = None
        self.current_model_name = None
        self.generate_worker = None
        self.load_worker = None

    def load_model(self, repo_id, filename):
        self.model_loading.emit()
        self.load_worker = ModelLoadWorker(repo_id, filename)
        self.load_worker.progress.connect(self.model_download_progress)
        self.load_worker.finished.connect(self.on_model_loaded)
        self.load_worker.error.connect(self.on_model_error)
        self.load_worker.start()

    def on_model_loaded(self, model):
        self.model = model
        self.current_model_name = self.load_worker.filename
        logging.info(f"Model loaded successfully: {self.current_model_name}")
        self.model_loaded.emit(self.current_model_name)
        
    def on_model_error(self, error):
        error_msg = f"Failed to load model: {error}"
        logging.error(error_msg)
        self.model_error.emit(error_msg)

    def set_system_message(self, message):
        self.system_message = message

    def generate(self, messages, context=None, tokens=256):
        if hasattr(self, 'system_message'):
            messages = [{"role": "system", "content": self.system_message}] + messages
        
        max_tokens = tokens
        if not self.model:
            raise RuntimeError("Model not loaded. Please load a model first.")
        
        logging.debug(f"Generating response with context: {context}")
        
        try:
            self.generate_worker = GenerateWorker(self.model, messages, max_tokens)
            self.generate_worker.finished.connect(self.on_generation_finished)
            self.generate_worker.error.connect(self.on_generation_error)
            self.generate_worker.partial_response.connect(self.partial_response)
            self.generate_worker.start()
        except Exception as e:
            logging.error(f"Error in generate method: {e}")
            raise

    def on_generation_finished(self, response):
        self.generation_finished.emit(response)

    def on_generation_error(self, error):
        logging.error(f"Generation error: {error}")
        self.generation_error.emit(str(error))

    def get_model_size(self, model_name=None):
        if model_name is None:
            model_name = self.current_model_name
        
        if model_name is None:
            logging.warning("No model specified and no current model loaded.")
            return 0
        
        model_path = os.path.join(self.models_dir, model_name)
        if not os.path.exists(model_path):
            logging.error(f"Model file not found: {model_path}")
            return 0
        
        return os.path.getsize(model_path)

   

   
