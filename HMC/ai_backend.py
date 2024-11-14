from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Union
from dataclasses import dataclass
import logging
import openai
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

@dataclass
class AIConfig:
    model_type: ModelType
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.95
    frequency_penalty: float = 0
    presence_penalty: float = 0
    api_key: Optional[str] = None
    model_path: Optional[str] = None

class AIBackend(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def stream(self, prompt: str, callback, **kwargs):
        pass

class LlamaBackend(AIBackend):
    def __init__(self, config: AIConfig):
        try:
            from llama_cpp import Llama
            self.model = Llama.from_pretrained(
                repo_id=config.model_path,
                filename=config.model_name,
                n_ctx=6000
            )
            self.config = config
        except Exception as e:
            logger.error(f"Failed to initialize Llama: {e}")
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.model.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                **kwargs
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Llama generation error: {e}")
            return f"Error generating response: {str(e)}"

    async def stream(self, prompt: str, callback, **kwargs):
        try:
            response = self.model.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                stream=True,
                **kwargs
            )
            for chunk in response:
                if chunk and chunk.choices and chunk.choices[0].delta.content:
                    callback(chunk.choices[0].delta.content)
        except Exception as e:
            logger.error(f"Llama streaming error: {e}")
            callback(f"Error streaming response: {str(e)}")

class AnthropicBackend(AIBackend):
    def __init__(self, config: AIConfig):
        try:
            import anthropic
            self.client = anthropic.Client(api_key=config.api_key)
            self.config = config
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.completion(
                model=self.config.model_name,
                prompt=prompt,
                max_tokens_to_sample=self.config.max_tokens,
                temperature=self.config.temperature,
                **kwargs
            )
            return response.completion
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            return f"Error generating response: {str(e)}"

    async def stream(self, prompt: str, callback, **kwargs):
        try:
            response = self.client.completion_stream(
                model=self.config.model_name,
                prompt=prompt,
                max_tokens_to_sample=self.config.max_tokens,
                temperature=self.config.temperature,
                **kwargs
            )
            async for chunk in response:
                if chunk.completion:
                    callback(chunk.completion)
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            callback(f"Error streaming response: {str(e)}")

class OpenAIBackend(AIBackend):
    def __init__(self, config: AIConfig):
        try:
            import openai
            openai.api_key = config.api_key
            self.config = config
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            return f"Error generating response: {str(e)}"

    async def stream(self, prompt: str, callback, **kwargs):
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
                **kwargs
            )
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    callback(chunk.choices[0].delta.content)
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            callback(f"Error streaming response: {str(e)}")

def create_ai_backend(config: AIConfig) -> AIBackend:
    backends = {
        ModelType.LOCAL: LlamaBackend,
        ModelType.ANTHROPIC: AnthropicBackend,
        ModelType.OPENAI: OpenAIBackend
    }
    
    if config.model_type not in backends:
        raise ValueError(f"Unknown model type: {config.model_type}")
    
    return backends[config.model_type](config) 