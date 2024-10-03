import tiktoken
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from transformers import AutoTokenizer, BasicTokenizer
import logging

class ContextManager:
    def __init__(self, cccore, max_tokens=4000, max_file_size=1024*1024, model_name="arcee-ai/Llama-3.1-SuperNova-Lite"):
        self.cccore = cccore
        self.max_tokens = max_tokens
        self.max_file_size = max_file_size
        self.tokenizer = self.load_tokenizer(model_name)
        self.contexts = []
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def load_tokenizer(self, model_name):
        try:
            return AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            logging.warning(f"Failed to load AutoTokenizer: {e}")
            return tiktoken.get_encoding("cl100k_base")  # Fallback to tiktoken

    def add_context(self, content, description):
        tokens = self.tokenize(content)
        if len(tokens) > self.max_tokens:
            content = self.detokenize(tokens[:self.max_tokens])
        self.contexts.append((description, content))
        self.prune_contexts()

    def prune_contexts(self):
        while self.get_total_tokens() > self.max_tokens:
            self.contexts.pop(0)

    def get_context(self):
        return "\n\n".join([f"{desc}:\n{content}" for desc, content in self.contexts])

    def tokenize(self, text):
        if isinstance(self.tokenizer, tiktoken.Encoding):
            return self.tokenizer.encode(text)
        return self.tokenizer.encode(text, add_special_tokens=False)

    def detokenize(self, tokens):
        if isinstance(self.tokenizer, tiktoken.Encoding):
            return self.tokenizer.decode(tokens)
        return self.tokenizer.decode(tokens)

    def get_total_tokens(self):
        return sum(len(self.tokenize(content)) for _, content in self.contexts)

    def is_file_too_large(self, file_path):
        return os.path.getsize(file_path) > self.max_file_size

    def get_most_relevant_context(self, query, top_n=3):
        if not self.contexts:
            return ""
        
        all_contexts = [content for _, content in self.contexts]
        tfidf_matrix = self.vectorizer.fit_transform(all_contexts + [query])
        cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
        most_similar_indices = cosine_similarities.argsort()[-top_n:][::-1]
        
        relevant_contexts = [self.contexts[i] for i in most_similar_indices]
        return "\n\n".join([f"{desc}:\n{content}" for desc, content in relevant_contexts])
    def get_contexts(self):
        return self.contexts
    def get_context_by_description(self, description):
        for desc, content in self.contexts:
            if desc == description:
                return content
        return None
    def remove_context_by_description(self, description):
        self.contexts = [context for context in self.contexts if context[0] != description]
    def clear_contexts(self):
        self.contexts = []
    
    def get_context_sizes(self):
        return [len(self.tokenize(content)) for _, content in self.contexts]
    def get_context_sizes_in_tokens(self):
        return [len(self.tokenize(content)) for _, content in self.contexts]
 

class NoveltyDetector:
    def __init__(self, threshold=0.3):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.threshold = threshold

    def get_novel_parts(self, content):
        sentences = content.split('.')
        if len(sentences) < 2:
            return [content]

        tfidf_matrix = self.vectorizer.fit_transform(sentences)
        pairwise_similarities = cosine_similarity(tfidf_matrix)

        novel_parts = []
        for i, sentence in enumerate(sentences):
            if i == 0 or np.max(pairwise_similarities[i, :i]) < self.threshold:
                novel_parts.append(sentence)

        return novel_parts
    
