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
            full_description = f"File: {os.path.abspath(file_path)}"
            full_content = f"{full_description}\n\n{content}"
        else:
            full_description = description
            full_content = content
        
        tokens = self.tokenize(full_content)
        if len(tokens) > self.max_tokens:
            full_content = self.detokenize(tokens[:self.max_tokens])
        
        self.memory_manager.add_memory(full_description, full_content, memory_type)
        self.contexts.append((full_description, full_content))
        self.prune_contexts()
        logging.warning(f"Added context: {full_description}")
        logging.warning(f"Contexts: {full_content}")

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

    def extract_code_blocks(self, content):
        code_block_pattern = r'```(\w+)?\n(.*?)```'
        return re.findall(code_block_pattern, content, re.DOTALL)

    def process_code_blocks(self, blocks):
        processed_blocks = []
        for lang, code in blocks:
            if lang.lower() == 'diff':
                processed_code = self.process_diff(code)
            else:
                processed_code = code  # Keep the original code for non-diff blocks
            processed_blocks.append((lang, processed_code))
        return processed_blocks

    def process_diff(self, diff_content):
        lines = diff_content.split('\n')
        file_path = None
        processed_lines = []

        for line in lines:
            if line.startswith('```') and ':' in line:
                file_path = line.split(':', 1)[1].strip()
                processed_lines.append(f"```diff:{file_path}")
            elif line.startswith(('+', '-', ' ')):
                processed_lines.append(line)
            elif not line.strip():
                processed_lines.append(line)  # Keep empty lines

        if file_path:
            return '\n'.join(processed_lines)
        else:
            return diff_content  # Return original content if no file path found

    def get_most_relevant_context(self, query, top_n=3):
        # Get relevant memories from the memory manager
        relevant_memories = self.memory_manager.get_relevant_memories(query, top_n)
        
        # Get contexts from selected files
        file_contexts = [(desc, content) for desc, content in self.contexts if desc.startswith("File:")]
        
        # Combine memories and file contexts
        all_contexts = relevant_memories + file_contexts
        
        # Sort contexts by relevance (assuming memories are already sorted)
        sorted_contexts = sorted(all_contexts, key=lambda x: x[2] if len(x) > 2 else 0, reverse=True)
        
        # Take top_n contexts
        top_contexts = sorted_contexts[:top_n]
        
        logging.debug(f"Top contexts: {top_contexts}")
        return top_contexts

    def preprocess_message(self, message):
        code_blocks = self.extract_code_blocks(message)
        processed_blocks = self.process_code_blocks(code_blocks)
        
        # Replace original code blocks with processed ones
        for (lang, original), (_, processed) in zip(code_blocks, processed_blocks):
            original_block = f"```{lang}\n{original}\n```"
            processed_block = f"```{lang}\n{processed}\n```"
            message = message.replace(original_block, processed_block)

        relevant_contexts = self.get_most_relevant_context(message)
        logging.warning(f"Relevant contexts: {relevant_contexts}")
        processed_contexts = self.process_contexts(relevant_contexts)
        
        context_info = ""
        for context in processed_contexts:
            if len(context) == 2:
                desc, content = context
            elif len(context) == 3:
                desc, content, _ = context
            else:
                logging.warning(f"Unexpected context format: {context}")
                continue
            
            if desc.startswith("File:"):
                file_path = desc.split("File: ", 1)[1]
                context_info += f"File: {file_path}\n\n{content}\n\n"
            else:
                context_info += f"{desc}:\n{content}\n\n"
        
        # Prepend context information to the message
        message = f"{context_info}\n{message}"
        
        logging.warning(f"Preprocessed message with context (first 1000 chars): {message[:1000]}...")
        logging.debug(f"Full preprocessed message: {message}")
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
            
            if desc.startswith("File:"):
                file_path = desc.split("File: ", 1)[1]
                if self.is_code_file(file_path):
                    processed_content = self.reduce_code_tokens(content)
                else:
                    processed_content = content
                processed_contexts.append((f"File: {os.path.abspath(file_path)}", processed_content))
            else:
                processed_contexts.append((desc, content))
        return processed_contexts

    def is_code_file(self, file_path):
        code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go']
        return any(file_path.lower().endswith(ext) for ext in code_extensions)

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


