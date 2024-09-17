import tiktoken
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from transformers import LlamaTokenizer, AutoTokenizer, BasicTokenizer
import logging

class ContextManager:
    def __init__(self, max_tokens=4000, max_file_size=1024*1024, model_name="arcee-ai/Llama-3.1-SuperNova-Lite"):
        self.max_tokens = max_tokens
        self.max_file_size = max_file_size
        self.tokenizer = self.load_tokenizer(model_name)
        self.contexts = []
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def load_tokenizer(self, model_name):
        try:
            return LlamaTokenizer.from_pretrained(model_name)
        except Exception as e:
            logging.warning(f"Failed to load LlamaTokenizer: {e}")
            try:
                return AutoTokenizer.from_pretrained("gpt2")  # Fallback to GPT-2 tokenizer
            except Exception as e:
                logging.warning(f"Failed to load AutoTokenizer: {e}")
                return tiktoken.get_encoding("cl100k_base")  # Fallback to tiktoken

    def tokenize(self, text):
        if hasattr(self.tokenizer, 'encode'):
            return self.tokenizer.encode(text, add_special_tokens=False)
        else:
            # Fallback for BasicTokenizer
            return self.tokenizer.tokenize(text)

    def detokenize(self, tokens):
        if hasattr(self.tokenizer, 'decode'):
            return self.tokenizer.decode(tokens)
        else:
            # Fallback for BasicTokenizer
            return " ".join(tokens)

    def add_context(self, context, description):
        tokens = self.tokenize(context)
        if len(tokens) > self.max_tokens:
            truncated_tokens = tokens[:self.max_tokens]
            truncated_context = self.detokenize(truncated_tokens)
            self.contexts.append((truncated_context, description, len(truncated_tokens)))
        else:
            self.contexts.append((context, description, len(tokens)))
        self.prune_context()

    def prune_context(self):
        while self.get_total_tokens() > self.max_tokens:
            if len(self.contexts) > 1:
                self.remove_least_relevant()
            else:
                self.truncate_context()

    def remove_least_relevant(self):
        if len(self.contexts) < 2:
            return

        # Compute TF-IDF matrix
        tfidf_matrix = self.vectorizer.fit_transform([ctx for ctx, _, _ in self.contexts])

        # Compute pairwise similarities
        similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]

        # Find the least similar (relevant) context
        least_relevant_index = similarities.argmin()

        # Remove the least relevant context
        del self.contexts[least_relevant_index]

    def truncate_context(self):
        if not self.contexts:
            return
        context, description, _ = self.contexts[0]
        tokens = self.tokenize(context)
        truncated_tokens = tokens[:self.max_tokens]
        truncated_context = self.detokenize(truncated_tokens)
        self.contexts[0] = (truncated_context, description, len(truncated_tokens))

    def get_context(self):
        return "\n".join(f"{desc}:\n{ctx}" for ctx, desc, _ in self.contexts)

    def get_total_tokens(self):
        return sum(tokens for _, _, tokens in self.contexts)

    def is_file_too_large(self, file_path):
        return os.path.getsize(file_path) > self.max_file_size