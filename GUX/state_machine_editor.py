from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QGroupBox, QLabel, QLineEdit, 
                            QComboBox, QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
import tempfile

class StateMachineEditor(QDialog):
    def __init__(self, state_machine, parent=None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.visualizer = StateMachineVisualizer(state_machine)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("State Machine Editor")
        self.resize(1200, 800)
        
        layout = QHBoxLayout(self)
        
        # Left panel: State and transition editor
        editor_panel = QVBoxLayout()
        
        # States list
        states_group = QGroupBox("States")
        states_layout = QVBoxLayout()
        self.states_list = QListWidget()
        self.states_list.addItems(self.get_all_states())
        states_layout.addWidget(self.states_list)
        
        # Add state controls
        add_state_layout = QHBoxLayout()
        self.new_state_input = QLineEdit()
        add_state_btn = QPushButton("Add State")
        add_state_btn.clicked.connect(self.add_state)
        add_state_layout.addWidget(self.new_state_input)
        add_state_layout.addWidget(add_state_btn)
        states_layout.addLayout(add_state_layout)
        
        states_group.setLayout(states_layout)
        editor_panel.addWidget(states_group)
        
        # Transitions editor
        transitions_group = QGroupBox("Transitions")
        transitions_layout = QVBoxLayout()
        
        # From/To state selectors
        transition_controls = QHBoxLayout()
        self.from_state = QComboBox()
        self.to_state = QComboBox()
        self.from_state.addItems(self.get_all_states())
        self.to_state.addItems(self.get_all_states())
        transition_controls.addWidget(QLabel("From:"))
        transition_controls.addWidget(self.from_state)
        transition_controls.addWidget(QLabel("To:"))
        transition_controls.addWidget(self.to_state)
        transitions_layout.addLayout(transition_controls)
        
        # Required fields
        self.required_fields = QLineEdit()
        self.required_fields.setPlaceholderText("Required fields (comma-separated)")
        transitions_layout.addWidget(QLabel("Required Fields:"))
        transitions_layout.addWidget(self.required_fields)
        
        # Add transition button
        add_transition_btn = QPushButton("Add Transition")
        add_transition_btn.clicked.connect(self.add_transition)
        transitions_layout.addWidget(add_transition_btn)
        
        transitions_group.setLayout(transitions_layout)
        editor_panel.addWidget(transitions_group)
        
        layout.addLayout(editor_panel)
        
        # Right panel: Visualization
        viz_panel = QVBoxLayout()
        self.web_view = QWebEngineView()
        viz_panel.addWidget(self.web_view)
        
        # Refresh visualization button
        refresh_btn = QPushButton("Refresh Visualization")
        refresh_btn.clicked.connect(self.refresh_visualization)
        viz_panel.addWidget(refresh_btn)
        
        layout.addLayout(viz_panel)
        
        # Initial visualization
        self.refresh_visualization()
    
    def get_all_states(self) -> List[str]:
        states = set()
        for from_state in self.state_machine.transitions:
            states.add(from_state)
            for to_state in self.state_machine.transitions[from_state]:
                states.add(to_state)
        return sorted(list(states))
    
    def add_state(self):
        new_state = self.new_state_input.text().strip()
        if new_state:
            self.states_list.addItem(new_state)
            self.from_state.addItem(new_state)
            self.to_state.addItem(new_state)
            self.new_state_input.clear()
            self.refresh_visualization()
    
    def add_transition(self):
        from_state = self.from_state.currentText()
        to_state = self.to_state.currentText()
        required_fields = {f.strip() for f in self.required_fields.text().split(',')}
        
        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            conditions=[],  # Add condition editor if needed
            side_effects=[],  # Add side effect editor if needed
            required_fields=required_fields
        )
        
        self.state_machine.add_transition(transition)
        self.refresh_visualization()
    
    def refresh_visualization(self):
        dot = self.visualizer.generate_dot()
        
        # Save to temporary file and display
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
            dot.render(f.name, format='svg')
            self.web_view.load(f"file://{f.name}.svg") 