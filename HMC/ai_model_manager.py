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
    finished = pyqtSignal(str, str)  # response, chat_type
    error = pyqtSignal(str, str)  # error message, chat_type
    partial_response = pyqtSignal(str, str)  # partial response, chat_type

    def __init__(self, model, messages, max_tokens, chat_type):
        super().__init__()
        self.model = model
        self.messages = messages
        self.max_tokens = max_tokens
        self.chat_type = chat_type

    def run(self):
        try:
            response = self.model.create_chat_completion(
                messages=self.messages,
                max_tokens=self.max_tokens
            )
            for partial in response['choices'][0]['message']['content']:
                self.partial_response.emit(partial, self.chat_type)
            self.finished.emit(response['choices'][0]['message']['content'], self.chat_type)
        except Exception as e:
            self.error.emit(str(e), self.chat_type)

class ModelManager(QObject):
    model_loading = pyqtSignal()
    model_loaded = pyqtSignal(str)
    model_error = pyqtSignal(str)
    model_download_progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes
    generation_finished = pyqtSignal(str, str)  # response, chat_type
    generation_error = pyqtSignal(str, str)  # error message, chat_type
    partial_response = pyqtSignal(str, str)  # partial response, chat_type
    memory_manager = AIMemoryManager()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.local_model = None
        self.openai_client = None
        self.anthropic_client = None
        self.current_local_model_name = None
        self.current_remote_model_name = None
        self.generate_worker = None
        self.load_worker = None
        self.static_model_name = "Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF"  # Add this line

    def load_model(self, model_type, filename, repo_id=None):
        self.model_loading.emit()
        if model_type == 'local':
            if repo_id is None:
                repo_id = "Joseph717171/Llama-3.1-SuperNova-Lite-8.0B-OQ8_0.EF32.IQ4_K-Q8_0-GGUF"
            
            self.load_worker = ModelLoadWorker(repo_id, filename)
            self.load_worker.progress.connect(self.model_download_progress)
            self.load_worker.finished.connect(self.on_local_model_loaded)
            self.load_worker.error.connect(self.on_local_model_load_error)  # Change this line
            self.load_worker.start()
        elif model_type == 'remote':
            self.current_remote_model_name = filename
            self.model_loaded.emit(f"Remote: {self.current_remote_model_name}")

    def generate(self, messages, chat_type, model_name):
        if chat_type == 'local':
            if self.local_model is None:
                self.load_model('local', model_name)
           
            self.generate_worker = GenerateWorker(self.local_model, messages, 1000, chat_type)
            self.generate_worker.finished.connect(self.generation_finished)
            self.generate_worker.error.connect(self.generation_error)
            self.generate_worker.partial_response.connect(self.partial_response)
            self.generate_worker.start()
        
            
        elif chat_type == 'remote':
            if not self.current_remote_model_name:
                raise ValueError("Remote model is not configured. Please set up the remote model first.")
            
            if self.current_remote_model_name in ['gpt-3.5-turbo', 'gpt-4']:
                response = openai.ChatCompletion.create(
                    model=self.current_remote_model_name,
                    messages=messages
                )
                self.generation_finished.emit(response.choices[0].message.content, 'remote')
            elif self.current_remote_model_name in ['Claude-3-5-Sonnet-20240620']:
                client = anthropic.Client(api_key=self.settings['anthropic_api_key'])
                response = client.completion(
                    model=self.current_remote_model_name,
                    prompt="\n\n".join([f"{m['role']}: {m['content']}" for m in messages]),
                    max_tokens_to_sample=1000,
                )
                self.generation_finished.emit(response.completion, 'remote')

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

    def change_model(self, model_type, new_model):
        if model_type == 'local':
            self.current_local_model_name = new_model
        else:
            self.current_remote_model_name = new_model
        self.load_model(model_type, new_model)

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
