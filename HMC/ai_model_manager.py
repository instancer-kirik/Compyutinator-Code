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
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
nlp = spacy.load("en_core_web_sm")
from string import punctuation
from heapq import nlargest
from collections import Counter
# Define threshold

threshold = 0.5

class AIMemoryManager:
    def __init__(self):
        self.memory = []
        self.memory_model = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

    def add_memory(self, description, content):
        if self.should_remember(content):
            self.memory.append((description, content))

    def extract_keywords(self, content, top_n=5):
        # Process the text with spaCy
        doc = nlp(content)
        
        # Extract nouns and proper nouns as keywords
        keywords = [token.text for token in doc if token.pos_ in ('NOUN', 'PROPN')]
        
        # Get the most common keywords
        most_common_keywords = Counter(keywords).most_common(top_n)
        
        return [keyword for keyword, _ in most_common_keywords]

    def should_remember(self, content, recent_message):
        # Combine techniques to decide if content should be remembered
        relevance = self.score_relevance(content, recent_message)
        summary = self.summarize_content(content)
        keywords = self.extract_keywords(content)
        evaluation = self.evaluate_memory(content)
        
        # Decide based on combined criteria
        return relevance > 0.5 or evaluation

    def summarize_content(self, content):
        # Initialize a summarization pipeline
        summarization_model = pipeline("summarization", model="facebook/bart-large-cnn")
        # Use the model to generate a summary
        summary = summarization_model(content, max_length=130, min_length=30, do_sample=False)
        return summary[0]['summary_text']

    def score_relevance(self, context, message):
        # Use cosine similarity or another metric to score relevance
        tfidf_matrix = self.vectorizer.fit_transform([context, message])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2]).flatten()[0]
        return similarity

    def evaluate_memory(self, content):
        # Use the model to predict the importance of the content
        result = self.memory_model(content)
        return result[0]['label'] == 'LABEL_1'  # Adjust based on your model's labels

    def get_memory(self, description):
        for desc, content in self.memory:
            if desc == description:
                return content
        return None

    def clear_memory(self):
        self.memory = []

    def get_all_memories(self):
        return self.memory


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

    def generate(self, messages, context=None, tokens=256):
        max_tokens = tokens
        if not self.model:
            raise RuntimeError("Model not loaded. Please load a model first.")
        
        logging.debug(f"Generating response with context: {context}")
        
        try:
            self.generate_worker = GenerateWorker(self.model, messages, max_tokens)
            self.generate_worker.finished.connect(self.on_generation_finished)
            self.generate_worker.error.connect(self.on_generation_error)
            self.generate_worker.partial_response.connect(self.partial_response)  # Connect partial responses
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

   

    def get_installed_models(self):
        models = [f for f in os.listdir(self.models_dir) if f.endswith('.gguf')]
        complete_models = [model for model in models if self.check_model_integrity(model)]
        return complete_models

