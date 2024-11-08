from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QHBoxLayout, QFileDialog, 
    QDialogButtonBox, QMessageBox
)
from HMC.project_generators.kotlin_generator import KotlinProjectGenerator
import logging

class ProjectCreationDialog(QDialog):
    def __init__(self, cccore, parent=None):
        super().__init__(parent)
        self.cccore = cccore
        self.generators = {
            "Kotlin": KotlinProjectGenerator
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
        layout = QFormLayout(self)
        
        # Project name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("MyProject")
        layout.addRow("Project Name:", self.name_input)
        
        # Project type selector
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.generators.keys())
        self.type_combo.currentTextChanged.connect(self.update_templates)
        layout.addRow("Project Type:", self.type_combo)
        
        # Template selector
        self.template_combo = QComboBox()
        layout.addRow("Template:", self.template_combo)
        
        # Location selector
        location_layout = QHBoxLayout()
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("/path/to/project")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_location)
        location_layout.addWidget(self.location_input)
        location_layout.addWidget(self.browse_btn)
        layout.addRow("Location:", location_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        # Initialize templates
        self.update_templates()
        
    def update_templates(self):
        """Update available templates based on project type"""
        project_type = self.type_combo.currentText()
        self.template_combo.clear()
        self.template_combo.addItems(self.templates.get(project_type, []))
            
    def browse_location(self):
        """Open file dialog to choose project location"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Project Location",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.location_input.setText(directory)
            
    def accept(self):
        """Create the project when OK is clicked"""
        try:
            # Validate inputs
            project_name = self.name_input.text().strip()
            project_type = self.type_combo.currentText()
            template = self.template_combo.currentText()
            location = self.location_input.text().strip()
            
            if not all([project_name, location]):
                QMessageBox.warning(self, "Error", "Please fill in all fields")
                return
                
            # Get appropriate generator
            generator_class = self.generators.get(project_type)
            if not generator_class:
                raise ValueError(f"No generator found for {project_type}")
                
            # Generate project
            generator = generator_class(self.cccore)
            generator.generate_project(
                template_name=template.lower().replace(" ", "_"),
                project_path=location,
                project_name=project_name
            )
            
            # Add to project manager
            self.cccore.project_manager.add_project(project_name, location)
            
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
            logging.error(f"Project creation failed: {e}", exc_info=True) 