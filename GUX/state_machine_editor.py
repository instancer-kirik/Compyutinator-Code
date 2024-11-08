from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QLineEdit, QLabel, QComboBox, QWidget, 
                            QGraphicsView, QGraphicsScene)
from PyQt6.QtCore import Qt
from riskkit.state_machine import StateMachine, Transition
from riskkit.state_machine_viz import StateMachineVisualizer
import logging
import tempfile

class StateMachineEditor(QDialog):
    def __init__(self, state_machine: StateMachine, parent=None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.setWindowTitle("Risk State Machine Editor")
        self.setMinimumSize(800, 600)
        
        # Initialize UI
        self.setup_ui()
        self.load_state_machine()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left panel - Editor controls
        editor_panel = QVBoxLayout()
        
        # States section
        states_group = QVBoxLayout()
        states_group.addWidget(QLabel("States"))
        self.states_list = QListWidget()
        states_group.addWidget(self.states_list)
        
        # Add state controls
        add_state_layout = QHBoxLayout()
        self.add_state_input = QLineEdit()
        self.add_state_input.setPlaceholderText("New state name...")
        add_state_btn = QPushButton("Add State")
        add_state_btn.clicked.connect(self.add_state)
        add_state_layout.addWidget(self.add_state_input)
        add_state_layout.addWidget(add_state_btn)
        states_group.addLayout(add_state_layout)
        
        editor_panel.addLayout(states_group)
        
        # Transitions section
        transitions_group = QVBoxLayout()
        transitions_group.addWidget(QLabel("Transitions"))
        
        # From/To state selectors
        transition_controls = QHBoxLayout()
        self.from_state = QComboBox()
        self.to_state = QComboBox()
        transition_controls.addWidget(QLabel("From:"))
        transition_controls.addWidget(self.from_state)
        transition_controls.addWidget(QLabel("To:"))
        transition_controls.addWidget(self.to_state)
        transitions_group.addLayout(transition_controls)
        
        # Required fields
        self.required_fields = QLineEdit()
        self.required_fields.setPlaceholderText("Required fields (comma-separated)")
        transitions_group.addWidget(QLabel("Required Fields:"))
        transitions_group.addWidget(self.required_fields)
        
        # Add transition button
        add_transition_btn = QPushButton("Add Transition")
        add_transition_btn.clicked.connect(self.add_transition)
        transitions_group.addWidget(add_transition_btn)
        
        editor_panel.addLayout(transitions_group)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_changes)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        editor_panel.addLayout(buttons_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(editor_panel)
        layout.addWidget(left_widget)
        
        # Right panel - Visualization
        self.graph_view = QGraphicsView()
        self.graph_view.setScene(QGraphicsScene())
        layout.addWidget(self.graph_view)
        
    def load_state_machine(self):
        # Load existing states
        states = set()
        for from_state in self.state_machine.transitions:
            states.add(from_state)
            for to_state in self.state_machine.transitions[from_state]:
                states.add(to_state)
        
        # Update UI
        self.states_list.clear()
        self.from_state.clear()
        self.to_state.clear()
        
        for state in sorted(states):
            self.states_list.addItem(state)
            self.from_state.addItem(state)
            self.to_state.addItem(state)
        
        self.update_visualization()
        
    def add_state(self):
        state_name = self.add_state_input.text().strip()
        if state_name:
            self.states_list.addItem(state_name)
            self.from_state.addItem(state_name)
            self.to_state.addItem(state_name)
            self.add_state_input.clear()
            self.update_visualization()
    
    def add_transition(self):
        from_state = self.from_state.currentText()
        to_state = self.to_state.currentText()
        required_fields = {f.strip() for f in self.required_fields.text().split(',') if f.strip()}
        
        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            conditions=[],  # Add condition editor if needed
            side_effects=[],  # Add side effect editor if needed
            required_fields=required_fields
        )
        
        self.state_machine.add_transition(transition)
        self.update_visualization()
    
    def update_visualization(self):
        try:
            visualizer = StateMachineVisualizer(self.state_machine)
            dot = visualizer.generate_dot()
            
            # Save to temp file and display
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                dot.render(tmp.name, format='png', cleanup=True)
                scene = self.graph_view.scene()
                scene.clear()
                
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap(tmp.name + '.png')
                scene.addPixmap(pixmap)
                self.graph_view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            logging.error(f"Failed to update visualization: {e}")
    
    def save_changes(self):
        self.accept()