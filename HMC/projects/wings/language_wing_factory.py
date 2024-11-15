from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from ..wing_config import WingConfig
from ..project_wing import Wing
from ..project_types import WingType
from datetime import datetime
@dataclass
class LanguageWingFactory:
    """Factory for creating language-specific wings"""
    project_path: Path

    def detect_languages(self) -> list[str]:
        """Detect programming languages in project"""
        languages = []
        if self._has_python():
            languages.append("python")
        if self._has_mojo():
            languages.append("mojo")
        # Add other language detections
        return languages

    def create_wing(self, language: str) -> Optional[Wing]:
        """Create language-specific wing"""
        creators = {
            "python": self._create_python_wing,
            "mojo": self._create_mojo_wing
        }
        creator = creators.get(language)
        return creator() if creator else None

    def _has_python(self) -> bool:
        return (self.project_path / 'setup.py').exists() or bool(list(self.project_path.glob('*.py')))

    def _has_mojo(self) -> bool:
        return bool(list(self.project_path.glob('*.mojo')))

    def _create_python_wing(self) -> Wing:
        config = WingConfig()
        config.build.update({
            "command": "python setup.py build",
            "dependencies": ["setuptools", "wheel"],
            "scripts": {
                "test": "pytest",
                "lint": "flake8"
            }
        })
        config.runtime.update({
            "entry_points": {"main": "src/main.py"},
            "environment": {"PYTHONPATH": "src"},
            "requirements": ["requirements.txt"]
        })
        config.development.update({
            "tools": ["pytest", "flake8", "black"],
            "linters": ["flake8", "pylint"],
            "formatters": ["black"],
            "test_framework": "pytest"
        })

        return Wing(
            id=f"python_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="Python",
            type=WingType.LANGUAGE,
            description="Python language support",
            config=config,
            path=self.project_path / "wings" / "python"
        )

    def _create_mojo_wing(self) -> Wing:
        config = WingConfig()
        config.build.update({
            "command": "mojo build",
            "scripts": {
                "test": "mojo test",
                "benchmark": "mojo benchmark"
            }
        })
        config.runtime.update({
            "entry_points": {"main": "src/main.mojo"}
        })
        config.development.update({
            "tools": ["mojo-debug"],
            "formatters": ["mojo-fmt"],
            "test_framework": "mojo-test"
        })

        return Wing(
            id=f"mojo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="Mojo",
            type=WingType.LANGUAGE,
            description="Mojo language support",
            config=config,
            path=self.project_path / "wings" / "mojo"
        ) 