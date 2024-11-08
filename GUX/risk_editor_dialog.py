from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QComboBox, QSpinBox, QPushButton
)
from PyQt6.QtCore import Qt
from riskkit.enums import (
    RiskProbability, RiskStatus, ImpactSeverity,
    RewardType
)

class RiskEditorDialog(QDialog):
    def __init__(self, risk_data=None, parent=None):
        super().__init__(parent)
        self.risk_data = risk_data
        self.setup_ui()
        if risk_data:
            self.load_risk_data()
            
    def setup_ui(self):
        self.setWindowTitle("Risk Editor")
        layout = QVBoxLayout()
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description = QTextEdit()
        layout.addWidget(self.description)
        
        # Probability
        prob_layout = QHBoxLayout()
        prob_layout.addWidget(QLabel("Probability:"))
        self.probability = QComboBox()
        self.probability.addItems([p.value for p in RiskProbability])
        prob_layout.addWidget(self.probability)
        layout.addLayout(prob_layout)
        
        # Impact
        impact_layout = QHBoxLayout()
        impact_layout.addWidget(QLabel("Impact:"))
        self.impact = QComboBox()
        self.impact.addItems([i.value for i in ImpactSeverity])
        impact_layout.addWidget(self.impact)
        layout.addLayout(impact_layout)
        
        # Status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status = QComboBox()
        self.status.addItems([s.value for s in RiskStatus])
        status_layout.addWidget(self.status)
        layout.addLayout(status_layout)
        
        # Mitigation
        layout.addWidget(QLabel("Mitigation:"))
        self.mitigation = QTextEdit()
        layout.addWidget(self.mitigation)
        
        # Reward Type
        reward_layout = QHBoxLayout()
        reward_layout.addWidget(QLabel("Reward Type:"))
        self.reward_type = QComboBox()
        self.reward_type.addItems([r.value for r in RewardType])
        reward_layout.addWidget(self.reward_type)
        layout.addLayout(reward_layout)
        
        # Estimated Value
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Estimated Value:"))
        self.value = QSpinBox()
        self.value.setRange(0, 1000000)
        self.value.setSingleStep(1000)
        value_layout.addWidget(self.value)
        layout.addLayout(value_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def load_risk_data(self):
        """Load existing risk data into the form"""
        if self.risk_data:
            self.description.setText(self.risk_data.description)
            self.probability.setCurrentText(self.risk_data.probability.value)
            self.impact.setCurrentText(self.risk_data.impact.value)
            self.status.setCurrentText(self.risk_data.status.value)
            self.mitigation.setText(self.risk_data.mitigation)
            self.reward_type.setCurrentText(self.risk_data.reward_type.value)
            self.value.setValue(self.risk_data.estimated_value)
            
    def get_risk_data(self):
        """Get the form data as a dictionary"""
        return {
            "description": self.description.toPlainText(),
            "probability": self.probability.currentText(),
            "impact": self.impact.currentText(),
            "status": self.status.currentText(),
            "mitigation": self.mitigation.toPlainText(),
            "reward_type": self.reward_type.currentText(),
            "estimated_value": self.value.value()
        } 