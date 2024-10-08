import tiktoken
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from transformers import AutoTokenizer, BasicTokenizer
import logging
import re

class ContextManager:
    def __init__(self, cccore, max_tokens=4000, max_file_size=1024*1024, model_name="arcee-ai/Llama-3.1-SuperNova-Lite"):
        self.cccore = cccore
        self.max_tokens = max_tokens
        self.max_file_size = max_file_size
        self.tokenizer = self.load_tokenizer(model_name)
        self.memory_manager = cccore.model_manager.memory_manager #this is after the model manager is initialized
        self.contexts = []  # Keep this for backward compatibility

    def load_tokenizer(self, model_name):
        try:
            return AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            logging.warning(f"Failed to load AutoTokenizer: {e}")
            return tiktoken.get_encoding("cl100k_base")  # Fallback to tiktoken

    def add_context(self, content, description, file_path=None, memory_type='code'):
        if file_path:
            content = f"File: {file_path}\n\n{content}"
        tokens = self.tokenize(content)
        if len(tokens) > self.max_tokens:
            content = self.detokenize(tokens[:self.max_tokens])
        self.memory_manager.add_memory(description, content, memory_type)
        self.contexts.append((description, content))  # Keep this for backward compatibility
        self.prune_contexts()

    def prune_contexts(self):
        while self.get_total_tokens() > self.max_tokens:
            self.contexts.pop(0)
            # Also remove from memory_manager
            if self.contexts:
                self.memory_manager.code_memory.pop(0)

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
        relevant_memories = self.memory_manager.get_relevant_memories(query, top_n)
        logging.debug(f"Relevant memories: {relevant_memories}")
        return relevant_memories

    def extract_code_blocks(self, content):
        code_block_pattern = r'```(\w+)?\n(.*?)```'
        return re.findall(code_block_pattern, content, re.DOTALL)

    def process_code_blocks(self, blocks):
        processed_blocks = []
        for lang, code in blocks:
            processed_code = self.reduce_code_tokens(code)
            processed_blocks.append((lang, processed_code))
        return processed_blocks

    def preprocess_message(self, message):
        code_blocks = self.extract_code_blocks(message)
        processed_blocks = self.process_code_blocks(code_blocks)
        
        # Replace original code blocks with processed ones
        for (lang, original), (_, processed) in zip(code_blocks, processed_blocks):
            message = message.replace(f"```{lang}\n{original}```", f"```{lang}\n{processed}```")

        relevant_contexts = self.get_most_relevant_context(message)
        processed_contexts = self.process_contexts(relevant_contexts)
        return message, processed_contexts

    def process_contexts(self, contexts):
        processed_contexts = []
        for context in contexts:
            if len(context) == 2:
                desc, content = context
            elif len(context) == 3:
                desc, content, _ = context
            else:
                logging.warning(f"Unexpected context format: {context}")
                continue
            
            if self.is_code_file(desc):
                processed_content = self.reduce_code_tokens(content)
            else:
                processed_content = content
            processed_contexts.append((desc, processed_content))
        return processed_contexts

    def is_code_file(self, file_path):
        code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go']
        return any(file_path.endswith(ext) for ext in code_extensions)

    def reduce_code_tokens(self, code_content):
        code_blocks = re.split(r'\n(?=\S)', code_content)
        
        reduced_blocks = []
        for block in code_blocks:
            if self.is_relevant_code_block(block):
                reduced_blocks.append(block)
            else:
                reduced_blocks.append(self.fold_code_block(block))
        
        return '\n'.join(reduced_blocks)

    def is_relevant_code_block(self, block):
        relevant_keywords = ['def ', 'class ', 'import ', 'from ', 'if __name__']
        return any(keyword in block for keyword in relevant_keywords)

    def fold_code_block(self, block):
        lines = block.split('\n')
        if len(lines) > 1:
            return f"{lines[0]} # ... ({len(lines)} lines)"
        return block

    def get_contexts(self):
        return self.contexts
    def get_context_by_description(self, description):
        for desc, content in self.contexts:
            if desc == description:
                return content
        return None
    def remove_context_by_description(self, description):
        self.contexts = [context for context in self.contexts if context[0] != description]
        # Also remove from memory_manager
        self.memory_manager.code_memory = [mem for mem in self.memory_manager.code_memory if mem[0] != description]

    def clear_contexts(self):
        self.contexts = []
        self.memory_manager.clear_memory('code')

    def get_context_sizes(self):
        return [len(self.tokenize(content)) for _, content in self.contexts]

    def get_context_sizes_in_tokens(self):
        return [len(self.tokenize(content)) for _, content in self.contexts]

    def add_project_info(self, info_type, content):
        self.memory_manager.add_project_info(info_type, content)


