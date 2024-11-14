import tiktoken
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from transformers import AutoTokenizer, BasicTokenizer
import logging
import re
from typing import Dict, List
from .symbol_manager import SymbolManager, CodeSymbol, SymbolReference
from pathlib import Path

class ContextManager:
    def __init__(self, cccore, max_tokens=4000):
        self.cccore = cccore
        self.max_tokens = max_tokens
        self.tokenizer = self.load_tokenizer("arcee-ai/Llama-3.1-SuperNova-Lite")
        self.memory_manager = None
        self.code_manager = cccore.code_manager
        self.symbol_manager = self.code_manager.symbol_manager
        self.contexts = []

    def setup_memory_manager(self, memory_manager):
        """Set up memory manager after initialization"""
        self.memory_manager = memory_manager

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

    def get_relevant_context(self, prompt: str) -> str:
        """Get relevant context based on prompt"""
        relevant_contexts = []
        
        # Get code contexts
        code_contexts = self._get_relevant_code_contexts(prompt)
        if code_contexts:
            relevant_contexts.extend(code_contexts)
            
        # Get project contexts
        project_contexts = self._get_relevant_project_contexts(prompt)
        if project_contexts:
            relevant_contexts.extend(project_contexts)
            
        return "\n\n".join(relevant_contexts) if relevant_contexts else ""

    def _get_relevant_code_contexts(self, prompt: str) -> list:
        """Get relevant code contexts using both symbol and code analysis"""
        contexts = []
        
        # Get symbol-based contexts
        symbols = self.symbol_manager.get_relevant_symbols(prompt)
        for symbol in symbols:
            # Get symbol references
            references = self.symbol_manager.get_symbol_references(symbol.name)
            context = self._format_symbol_context(symbol, references)
            contexts.append(context)
        
        # Get file-based contexts
        for file_path in self.code_manager.get_relevant_files(prompt):
            file_symbols = self.code_manager.get_file_symbols(file_path)
            file_refs = self.symbol_manager.get_file_references(file_path)
            context = self._format_file_context(file_path, file_symbols, file_refs)
            contexts.append(context)
            
        return contexts

    def _format_symbol_context(self, symbol: CodeSymbol, references: List[SymbolReference]) -> str:
        """Format symbol and its references into readable context"""
        parts = [f"Symbol: {symbol.name} ({symbol.type})"]
        parts.append(f"Defined in: {symbol.file_path}:{symbol.line}")
        
        if references:
            parts.append("\nReferences:")
            for ref in references:
                parts.append(f"- {ref.reference_type} in {ref.file_path}:{ref.line}")
                parts.append(f"  Context: {ref.context}")
                
        return "\n".join(parts)

    def _format_file_context(self, file_path: Path, symbols: List[CodeSymbol], references: Dict[str, List[SymbolReference]]) -> str:
        """Format file symbols and references into readable context"""
        parts = [f"File: {file_path}"]
        
        if symbols:
            parts.append("\nSymbols:")
            for symbol in symbols:
                parts.append(f"- {symbol.type}: {symbol.name} (line {symbol.line})")
                if symbol.children:
                    for child in symbol.children:
                        parts.append(f"  └─ {child.type}: {child.name}")
                        
        if references:
            parts.append("\nReferences:")
            for symbol_name, refs in references.items():
                parts.append(f"- {symbol_name}:")
                for ref in refs:
                    parts.append(f"  └─ {ref.reference_type} at line {ref.line}")
                    
        return "\n".join(parts)

    def _get_relevant_project_contexts(self, prompt: str) -> list:
        """Get relevant project-level contexts"""
        return [ctx for ctx in self.contexts if self._is_context_relevant(prompt, ctx[1])]

    def _is_context_relevant(self, prompt: str, context: str) -> bool:
        """Check if the context is relevant to the prompt"""
        # Implement your relevance logic here
        return True

    # def preprocess_message(self, message):
    #     code_blocks = self.extract_code_blocks(message)
    #     processed_blocks = self.process_code_blocks(code_blocks)
        
    #     # Replace original code blocks with processed ones
    #     for (lang, original), (_, processed) in zip(code_blocks, processed_blocks):
    #         original_block = f"```{lang}\n{original}\n```"
    #         processed_block = f"```{lang}\n{processed}\n```"
    #         message = message.replace(original_block, processed_block)

    #     relevant_contexts = self.get_most_relevant_context(message)
    #     logging.warning(f"Relevant contexts: {relevant_contexts}")
    #     processed_contexts = self.process_contexts(relevant_contexts)
        
    #     context_info = ""
    #     for context in processed_contexts:
    #         if len(context) == 2:
    #             desc, content = context
    #         elif len(context) == 3:
    #             desc, content, _ = context
    #         else:
    #             logging.warning(f"Unexpected context format: {context}")
    #             continue
            
    #         if desc.startswith("File:"):
    #             file_path = desc.split("File: ", 1)[1]
    #             context_info += f"File: {file_path}\n\n{content}\n\n"
    #         else:
    #             context_info += f"{desc}:\n{content}\n\n"
        
    #     # Prepend context information to the message
    #     message = f"{context_info}\n{message}"
        
    #     logging.warning(f"Preprocessed message with context (first 1000 chars): {message[:1000]}...")
    #     logging.debug(f"Full preprocessed message: {message}")
    #     return message, processed_contexts

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
                desc = desc.split("File:", 1)[1].strip()
            processed_contexts.append((f"File: {desc}", content))
        
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

    def add_technical_context(self, project_name: str):
        """Add technical context from project structure and symbols"""
        project_flow = self.cccore.project_manager.get_project_technical_flow(project_name)
        
        # Add project structure context
        structure_context = self._format_structure_context(project_flow['structure'])
        self.add_context(
            structure_context,
            "Project Structure",
            memory_type='technical'
        )
        
        # Add symbol relationships
        if 'relationships' in project_flow:
            relationship_context = self._format_relationship_context(project_flow['relationships'])
            self.add_context(
                relationship_context,
                "Symbol Relationships",
                memory_type='technical'
            )
    
    def _format_structure_context(self, structure: Dict) -> str:
        """Format project structure into readable context"""
        context_parts = []
        for file_path, info in structure.items():
            symbols = info.get('symbols', [])
            context_parts.append(f"File: {file_path}")
            
            for symbol in symbols:
                indent = "  " if symbol['parent'] is None else "    "
                symbol_type = symbol['type'].capitalize()
                context_parts.append(f"{indent}{symbol_type}: {symbol['name']} (line {symbol['line']})")
                
                if symbol['children']:
                    for child in symbol['children']:
                        context_parts.append(f"      - {child}")
        
        return "\n".join(context_parts)


