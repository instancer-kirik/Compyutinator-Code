from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QHBoxLayout, QFileDialog, 
    QDialogButtonBox, QMessageBox, QVBoxLayout, QLabel, QGroupBox, QListWidget, QInputDialog
)
from HMC.projects.project_generators.kotlin_generator import KotlinProjectGenerator
from HMC.projects.project_generators.existing_project import ExistingProjectGenerator
from pathlib import Path
import logging
from HMC.projects.project_config import ProjectConfig
from datetime import datetime

class ProjectCreationDialog(QDialog):
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.generators = {
            "Kotlin": KotlinProjectGenerator,
            "default": None
        }
        self.templates = {
            "Kotlin": ["Console App", "Android App", "Library"],
            "Python": ["Script", "Package", "Web App", "GUI App"],
            "C++": ["Console App", "Library", "Qt App"],
            "Web": ["Static Site", "React App", "Vue App"]
        }
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Create New Project")
        layout = QVBoxLayout(self)
        
        # Project Type
        type_layout = QHBoxLayout()
        type_label = QLabel("Project Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["New Project", "Existing Project"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Project Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Project Name:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Project Path
        path_layout = QHBoxLayout()
        path_label = QLabel("Project Path:")
        self.path_input = QLineEdit()
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def on_type_changed(self):
        if self.type_combo.currentText() == "Existing Project":
            self.name_input.setEnabled(False)
            self.path_input.setEnabled(True)
        else:
            self.name_input.setEnabled(True)
            self.path_input.setEnabled(False)
            
    def browse_path(self):
        if self.type_combo.currentText() == "Existing Project":
            path = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Parent Directory")
        if path:
            self.path_input.setText(path)
            if self.type_combo.currentText() == "Existing Project":
                self.name_input.setText(Path(path).name)
                
    def accept(self):
        """Create the project when OK is clicked"""
        try:
            project_data = {
                'name': self.name_input.text(),
                'path': self.path_input.text(),
                'type': self.type_combo.currentText()
            }
            
            if project_data['type'] == "Existing Project":
                generator = ExistingProjectGenerator(self.cccore)
            else:
                # Handle other project types
                pass
                
            # Get appropriate generator
            generator_class = self.generators.get(type,"default")
            if not generator_class:
                raise ValueError(f"No generator found for {type}")
                
            # Generate project
            generator = generator_class(self.cccore)
            generator.generate_project(
                project_data=project_data
            )
            
            # Add to project manager
            self.cccore.project_manager.add_project(project_data['name'], project_data['path'])
            
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
            logging.error(f"Project creation failed: {e}", exc_info=True) 

class ProjectConfigDialog(QDialog):
    def __init__(self, project_config: ProjectConfig, parent=None):
        super().__init__(parent)
        self.project_config = project_config
        self.setWindowTitle(f"Configure Project: {project_config.name}")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Basic Settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.project_config.name)
        self.description_edit = QLineEdit(self.project_config.description)
        self.status_combo = QComboBox()
        self.status_combo.addItems(['active', 'planning', 'on_hold', 'completed', 'archived'])
        self.status_combo.setCurrentText(self.project_config.status)
        
        basic_layout.addRow("Name:", self.name_edit)
        basic_layout.addRow("Description:", self.description_edit)
        basic_layout.addRow("Status:", self.status_combo)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Development Settings
        dev_group = QGroupBox("Development Settings")
        dev_layout = QFormLayout()
        
        self.build_command = QLineEdit(self.project_config.dev_settings['commands'].get('build', ''))
        self.run_command = QLineEdit(self.project_config.dev_settings['commands'].get('run', ''))
        self.test_command = QLineEdit(self.project_config.dev_settings['commands'].get('test', ''))
        
        dev_layout.addRow("Build Command:", self.build_command)
        dev_layout.addRow("Run Command:", self.run_command)
        dev_layout.addRow("Test Command:", self.test_command)
        
        # Scripts List
        self.scripts_list = QListWidget()
        self.scripts_list.addItems(self.project_config.dev_settings.get('scripts', []))
        dev_layout.addRow("Scripts:", self.scripts_list)
        
        # Script Buttons
        script_buttons = QHBoxLayout()
        add_script_btn = QPushButton("Add Script")
        remove_script_btn = QPushButton("Remove Script")
        add_script_btn.clicked.connect(self.add_script)
        remove_script_btn.clicked.connect(self.remove_script)
        script_buttons.addWidget(add_script_btn)
        script_buttons.addWidget(remove_script_btn)
        dev_layout.addRow("", script_buttons)
        
        dev_group.setLayout(dev_layout)
        layout.addWidget(dev_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_script(self):
        script, ok = QInputDialog.getText(self, "Add Script", "Enter script name:")
        if ok and script:
            self.scripts_list.addItem(script)

    def remove_script(self):
        current_item = self.scripts_list.currentItem()
        if current_item:
            self.scripts_list.takeItem(self.scripts_list.row(current_item))

    def get_updated_config(self) -> ProjectConfig:
        """Get updated configuration"""
        # Update basic settings
        self.project_config.name = self.name_edit.text()
        self.project_config.description = self.description_edit.text()
        self.project_config.status = self.status_combo.currentText()
        
        # Update development settings
        self.project_config.dev_settings['commands'].update({
            'build': self.build_command.text(),
            'run': self.run_command.text(),
            'test': self.test_command.text()
        })
        
        # Update scripts
        self.project_config.dev_settings['scripts'] = [
            self.scripts_list.item(i).text() 
            for i in range(self.scripts_list.count())
        ]
        
        # Update timestamp
        self.project_config.updated_at = datetime.now()
        
        return self.project_config
