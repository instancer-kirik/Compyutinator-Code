from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path

class ModelType(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

@dataclass
class TypingEffectConfig:
    enabled: bool = True
    speed: int = 50
    particle_count: int = 3

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
    model_path: Optional[Path] = None
    typing_effect: TypingEffectConfig = field(default_factory=TypingEffectConfig)

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization"""
        return {
            "model_type": self.model_type.value,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "api_key": self.api_key,
            "model_path": str(self.model_path) if self.model_path else None,
            "typing_effect": {
                "enabled": self.typing_effect.enabled,
                "speed": self.typing_effect.speed,
                "particle_count": self.typing_effect.particle_count
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AIConfig':
        """Create config from dictionary"""
        typing_effect = TypingEffectConfig(
            enabled=data.get("typing_effect", {}).get("enabled", True),
            speed=data.get("typing_effect", {}).get("speed", 50),
            particle_count=data.get("typing_effect", {}).get("particle_count", 3)
        )
        
        return cls(
            model_type=ModelType(data["model_type"]),
            model_name=data["model_name"],
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 2000),
            top_p=data.get("top_p", 0.95),
            frequency_penalty=data.get("frequency_penalty", 0),
            presence_penalty=data.get("presence_penalty", 0),
            api_key=data.get("api_key"),
            model_path=Path(data["model_path"]) if data.get("model_path") else None,
            typing_effect=typing_effect
        )

    @classmethod
    def default_local(cls) -> 'AIConfig':
        """Create default local model config"""
        return cls(
            model_type=ModelType.LOCAL,
            model_name="Llama-3.1-SuperNova-Lite",
            model_path=Path("models/Llama-3.1-SuperNova-Lite.gguf")
        )

    @classmethod
    def default_openai(cls, api_key: str) -> 'AIConfig':
        """Create default OpenAI config"""
        return cls(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key=api_key
        )

    @classmethod
    def default_anthropic(cls, api_key: str) -> 'AIConfig':
        """Create default Anthropic config"""
        return cls(
            model_type=ModelType.ANTHROPIC,
            model_name="claude-3-sonnet-20240229",
            api_key=api_key
        )
