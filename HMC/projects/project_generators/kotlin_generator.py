import os
import shutil
from typing import Dict, Any
from string import Template

class KotlinProjectGenerator:
    def __init__(self, cccore):
        self.cccore = cccore
        self.templates = {}
        
    def generate_project(self, template_name: str, project_path: str, project_name: str, options: Dict[str, Any] = None):
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
            
        template = self.templates[template_name]
        
        # Create project directory structure
        for dir_path, files in template["structure"].items():
            if dir_path == "root":
                full_path = project_path
            else:
                full_path = os.path.join(project_path, dir_path)
            os.makedirs(full_path, exist_ok=True)
            
            for file in files:
                self._create_file(template_name, dir_path, file, full_path, project_name, options)
        
        # Initialize Gradle wrapper if needed
        if template["build_system"] == "gradle":
            self._init_gradle_wrapper(project_path)
    
    def _create_file(self, template_name: str, dir_path: str, file: str, full_path: str, project_name: str, options: Dict[str, Any]):
        template_file = self._get_template_file(template_name, dir_path, file)
        
        if template_file:
            # Replace placeholders in template
            content = Template(template_file).safe_substitute(
                PROJECT_NAME=project_name,
                PACKAGE_NAME=project_name.lower().replace("-", "").replace(" ", ""),
                **options if options else {}
            )
        else:
            content = self._get_default_content(file, project_name)
            
        with open(os.path.join(full_path, file), 'w') as f:
            f.write(content)
    
    def _get_template_file(self, template_name: str, dir_path: str, file: str):
        # Load template file from resources
        template_path = os.path.join(
            self.cccore.settings_manager.get_value("templates_path"),
            "kotlin",
            template_name,
            dir_path,
            file + ".template"
        )
        
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
        return None
    
    def _get_default_content(self, file: str, project_name: str):
        # Default content for common files
        if file == "Main.kt":
            return f"""fun main() {{
    println("Hello from {project_name}!")
}}
"""
        elif file == "build.gradle.kts":
            return """plugins {
    kotlin("jvm") version "1.9.0"
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}
"""
        # Add more default templates as needed
        return ""
    
    def _init_gradle_wrapper(self, project_path: str):
        # Run gradle wrapper initialization
        # You might want to use your ProcessManager here
        pass 