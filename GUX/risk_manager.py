from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, 
                            QLabel, QComboBox, QTextEdit, QSpinBox, QFileDialog, 
                            QInputDialog, QMessageBox, QTabWidget, QGroupBox, 
                            QGridLayout, QDialog, QLineEdit, QRadioButton)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush, QKeySequence, QShortcut
from riskkit.schemas import (
    RiskBase, RiskCreate, RiskUpdate, RiskStatus, 
    RiskPriority, ValidationResult
)
from riskkit.risk import Risk
from riskkit.state_machine import RiskStateMachine, Transition
from riskkit.client import RiskkitClient, ApiConfig
from riskkit.enums import (
    RiskPriority, RiskStatus, RiskProbability, EventPriority,
    ImpactSeverity, ImpactArea, ImpactTimeframe, RewardType, ResourceType, RewardStatus, RewardTier
)
from riskkit.config import ConfigManager
from riskkit.validator import RiskValidator
from GUX.state_machine_editor import StateMachineEditor
from .risk_editor_dialog import RiskEditorDialog
from HMC.notification_manager import NotificationManager

import asyncio
import sys
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from riskkit.risk_repository import RiskRepository
from NITTY_GRITTY.database import DatabaseManager

class ConflictResolutionDialog(QDialog):
    def __init__(self, conflicts: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resolve Conflicts")
        self.conflicts = conflicts
        self.parent_window = parent
        self.radio_buttons = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create combo boxes
        self.setup_combo_boxes()
        
        # Add conflict resolution UI
        for field, values in self.conflicts.items():
            group = QGroupBox(f"Conflict in {field}")
            group_layout = QVBoxLayout()
            
            local_radio = QRadioButton(f"Local: {values['local']}")
            remote_radio = QRadioButton(f"Remote: {values['remote']}")
            local_radio.setChecked(True)
            
            self.radio_buttons[field] = (local_radio, remote_radio)
            
            group_layout.addWidget(local_radio)
            group_layout.addWidget(remote_radio)
            group.setLayout(group_layout)
            layout.addWidget(group)
        
        # Add buttons
        buttons = QHBoxLayout()
        accept = QPushButton("Accept Selected")
        cancel = QPushButton("Cancel")
        
        buttons.addWidget(accept)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        
        accept.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)

    def setup_combo_boxes(self):
        """Setup all combo boxes with their respective enum values"""
        # Create combo boxes
        self.reward_type_combo = QComboBox()
        self.probability_combo = QComboBox()
        self.impact_combo = QComboBox()
        self.status_combo = QComboBox()
        self.impact_area_combo = QComboBox()
        self.impact_timeframe_combo = QComboBox()
        self.resource_type_combo = QComboBox()
        
        # Update with enum values
        self.reward_type_combo.addItems([r.value for r in RewardType])
        self.probability_combo.addItems([p.value for p in RiskProbability])
        self.impact_combo.addItems([i.value for i in ImpactSeverity])
        self.status_combo.addItems([s.value for s in RiskStatus])
        self.impact_area_combo.addItems([ia.value for ia in ImpactArea])
        self.impact_timeframe_combo.addItems([it.value for it in ImpactTimeframe])
        self.resource_type_combo.addItems([rt.value for rt in ResourceType])
        
        # Set defaults
        self.reward_type_combo.setCurrentText(RewardType.OPTIMIZATION.value)
        self.probability_combo.setCurrentText(RiskProbability.POSSIBLE.value)
        self.impact_combo.setCurrentText(ImpactSeverity.MEDIUM.value)
        self.status_combo.setCurrentText(RiskStatus.OPEN.value)
    def get_resolved_data(self) -> dict:
        """Return resolved data based on selected radio buttons"""
        resolved = {}
        for field, (local, remote) in self.radio_buttons.items():
            resolved[field] = (
                self.conflicts[field]['local'] if local.isChecked() 
                else self.conflicts[field]['remote']
            )
        return resolved
class RiskManager(QMainWindow):
    # Add signals
    risk_created = pyqtSignal(dict)
    risk_updated = pyqtSignal(dict)
    risk_deleted = pyqtSignal(int)
    resource_updated = pyqtSignal(dict)
    news_received = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool)
    sync_status_changed = pyqtSignal(str)

    # Update weights to use enum values
    RISK_WEIGHTS = {
        RiskPriority.LOW.value: 1,
        RiskPriority.MEDIUM.value: 2,
        RiskPriority.HIGH.value: 3,
        RiskPriority.CRITICAL.value: 4
    }
    
    PROBABILITY_WEIGHTS = {
        RiskProbability.RARE.value: 0.1,
        RiskProbability.UNLIKELY.value: 0.3,
        RiskProbability.POSSIBLE.value: 0.5,
        RiskProbability.LIKELY.value: 0.7,
        RiskProbability.CERTAIN.value: 0.9
    }

    # Update color mappings to use enum values consistently
    COLORS = {
        # Priority colors
        RiskPriority.CRITICAL: QColor("#FF4444"),
        RiskPriority.HIGH: QColor("#FFA500"),
        RiskPriority.MEDIUM: QColor("#FFD700"),
        RiskPriority.LOW: QColor("#90EE90"),
        
        # Status colors
        RiskStatus.OPEN: QColor("#FFE4E1"),
        RiskStatus.IN_PROGRESS: QColor("#E0FFFF"),
        RiskStatus.MITIGATED: QColor("#98FB98"),
        RiskStatus.ACCEPTED: QColor("#DDA0DD"),
        RiskStatus.CLOSED: QColor("#98FB98"),
        RiskStatus.REJECTED: QColor("#FFB6C1"),  # Add missing status
        
        # Probability colors
        RiskProbability.RARE: QColor("#E0FFFF"),
        RiskProbability.UNLIKELY: QColor("#98FB98"),
        RiskProbability.POSSIBLE: QColor("#FFD700"),
        RiskProbability.LIKELY: QColor("#FFA500"),
        RiskProbability.CERTAIN: QColor("#FF4444"),
        
        # Impact colors
        ImpactSeverity.NEGLIGIBLE: QColor("#E0FFFF"),
        ImpactSeverity.LOW: QColor("#98FB98"),
        ImpactSeverity.MEDIUM: QColor("#FFD700"),
        ImpactSeverity.HIGH: QColor("#FFA500"),
        ImpactSeverity.CRITICAL: QColor("#FF4444"),
        
        # Reward type colors
        RewardType.OPTIMIZATION: QColor("#32CD32"),
        RewardType.REVENUE: QColor("#98FB98"),
        RewardType.EFFICIENCY: QColor("#87CEEB"),
        RewardType.QUALITY: QColor("#DDA0DD"),
        RewardType.STRATEGIC: QColor("#FFD700"),
        RewardType.OPPORTUNITY: QColor("#87CEEB"),
        RewardType.OTHER: QColor("#E0E0E0"),
    }

    # Update sample risks to use correct enum values
    SAMPLE_RISKS = [
        {
            "id": 1,
            "description": "Server Infrastructure Upgrade",
            "probability": RiskProbability.POSSIBLE.value,
            "impact": ImpactSeverity.HIGH.value,
            "priority": RiskPriority.HIGH.value,
            "status": RiskStatus.OPEN.value,
            "mitigation": "Planned phased rollout with fallback options",
            "reward_type": RewardType.OPTIMIZATION.value,
            "estimated_value": 50000,
            "reward_probability": RiskProbability.LIKELY.value,
            "date_created": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "id": 2,
            "description": "New Market Entry",
            "probability": RiskProbability.LIKELY.value,
            "impact": ImpactSeverity.CRITICAL.value,
            "priority": RiskPriority.HIGH.value,
            "status": RiskStatus.IN_PROGRESS.value,
            "mitigation": "Detailed market research and phased entry strategy",
            "reward_type": RewardType.REVENUE.value,
            "estimated_value": 200000,
            "reward_probability": RiskProbability.POSSIBLE.value,
            "date_created": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "id": 3,
            "description": "Legacy System Migration",
            "probability": RiskProbability.POSSIBLE.value,
            "impact": ImpactSeverity.MEDIUM.value,
            "priority": RiskPriority.MEDIUM.value,
            "status": RiskStatus.MITIGATED.value,
            "mitigation": "Comprehensive testing and backup procedures",
            "reward_type": RewardType.OPTIMIZATION.value,
            "estimated_value": 30000,
            "reward_probability": RiskProbability.LIKELY.value,
            "date_created": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
    ]

    def __init__(self, parent=None, cccore=None, config_manager=None, notification_manager=None):
        super().__init__(parent)
        self.cccore = cccore
        self.config_manager = config_manager or ConfigManager()
        self.notification_manager = notification_manager
        
        # Initialize repository
        self.repository = RiskRepository(cccore.db_manager if cccore else DatabaseManager('local'))
        self.repository.risks_updated.connect(self._on_risks_loaded)
        self.repository.risk_created.connect(self._on_risk_created)
        self.repository.risk_deleted.connect(self._on_risk_deleted)
        
        self.risks_cache = []
        
        # Initialize validator
        try:
            self.validator = RiskValidator()
        except Exception as e:
            logging.error(f"Failed to initialize RiskValidator: {e}")
            self.validator = None
        
        self.init_ui_components()
        self.setup_ui()
        self.load_data()

    def load_data(self):
        """Load risk data asynchronously"""
        try:
            project = self.cccore.project_manager.get_current_project() if self.cccore else None
            project_id = project.id if project else None
            
            # Clear existing data
            self.risk_table.setRowCount(0)
            self.show_info("Loading risks...")
            
            # Start async loading
            self.repository.load_risks_async(project_id)
            
        except Exception as e:
            logging.error(f"Error initiating risk data load: {e}")
            self.show_error("Failed to load risk data")

    def _on_risks_loaded(self, risks: List[Risk]):
        """Handle loaded risks"""
        try:
            self.risks_cache = risks
            
            # Update table
            self.risk_table.setRowCount(0)
            for risk in risks:
                self.add_risk_to_table(risk)
                
            self.risk_table.resizeColumnsToContents()
            self.show_info(f"Loaded {len(risks)} risks")
            
        except Exception as e:
            logging.error(f"Error processing loaded risks: {e}")
            self.show_error("Failed to process risk data")

    def init_ui_components(self):
        """Initialize UI components before setup"""
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.risk_tab = QWidget()
        self.dashboard_tab = QWidget()
        self.analysis_tab = QWidget()
        
        # Initialize UI elements
        self.risk_table = QTableWidget()
        self.risk_search = QLineEdit()
        self.filter_priority = QComboBox()
        self.filter_status = QComboBox()
        
        # Action buttons
        self.add_button = QPushButton("Add Risk")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.refresh_button = QPushButton("Refresh")
        
        # Risk details components
        self.description_text = QTextEdit()
        self.probability_combo = QComboBox()
        self.impact_combo = QComboBox()
        self.status_combo = QComboBox()
        self.mitigation_text = QTextEdit()
        
        # Reward components
        self.reward_type_combo = QComboBox()
        self.reward_value = QSpinBox()
        self.reward_probability = QSpinBox()
        
        # Status indicators
        self.connection_indicator = QLabel()
        self.sync_indicator = QLabel()
        
    def setup_ui(self):
        """Setup the UI layout and connections"""
        self.setWindowTitle("Risk Manager")
        self.resize(1200, 800)
        
        # Setup tabs
        self.tab_widget.addTab(self.risk_tab, "Risks")
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.analysis_tab, "Analysis")
        
        # Setup risk tab
        risk_layout = QVBoxLayout(self.risk_tab)
        
        # Search and filter bar
        filter_bar = QHBoxLayout()
        self.risk_search.setPlaceholderText("Search risks...")
        self.filter_priority.addItems(["All Priorities"] + [p.value for p in RiskPriority])
        self.filter_status.addItems(["All Statuses"] + [s.value for s in RiskStatus])
        
        filter_bar.addWidget(QLabel("Search:"))
        filter_bar.addWidget(self.risk_search)
        filter_bar.addWidget(QLabel("Priority:"))
        filter_bar.addWidget(self.filter_priority)
        filter_bar.addWidget(QLabel("Status:"))
        filter_bar.addWidget(self.filter_status)
        
        risk_layout.addLayout(filter_bar)
        
        # Risk table
        self.setup_risk_table()
        risk_layout.addWidget(self.risk_table)
        
        # Action buttons
        button_bar = QHBoxLayout()
        button_bar.addWidget(self.add_button)
        button_bar.addWidget(self.edit_button)
        button_bar.addWidget(self.delete_button)
        button_bar.addWidget(self.refresh_button)
        risk_layout.addLayout(button_bar)
        
        # Risk details
        details_group = QGroupBox("Risk Details")
        details_layout = QGridLayout()
        
        details_layout.addWidget(QLabel("Description:"), 0, 0)
        details_layout.addWidget(self.description_text, 0, 1)
        
        details_layout.addWidget(QLabel("Probability:"), 1, 0)
        details_layout.addWidget(self.probability_combo, 1, 1)
        
        details_layout.addWidget(QLabel("Impact:"), 2, 0)
        details_layout.addWidget(self.impact_combo, 2, 1)
        
        details_layout.addWidget(QLabel("Status:"), 3, 0)
        details_layout.addWidget(self.status_combo, 3, 1)
        
        details_layout.addWidget(QLabel("Mitigation:"), 4, 0)
        details_layout.addWidget(self.mitigation_text, 4, 1)
        
        details_group.setLayout(details_layout)
        risk_layout.addWidget(details_group)
        
        # Add tabs to main layout
        self.main_layout.addWidget(self.tab_widget)
        
        # Setup other tabs
        self.setup_dashboard_tab()
        self.setup_analysis_tab()
        
        # Connect signals
        self.connect_signals()
        
    def setup_risk_table(self):
        """Setup the risk table columns and properties"""
        self.risk_table.setColumnCount(6)
        self.risk_table.setHorizontalHeaderLabels([
            "ID", "Description", "Priority", "Status", "Last Updated", "Owner"
        ])
        self.risk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.risk_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.risk_table.horizontalHeader().setStretchLastSection(True)
        
    def connect_signals(self):
        """Connect all UI signals"""
        self.risk_table.itemClicked.connect(self.load_risk_details)
        self.add_button.clicked.connect(self.add_risk)
        self.edit_button.clicked.connect(self.edit_risk)
        self.delete_button.clicked.connect(self.delete_risk)
        self.refresh_button.clicked.connect(self.refresh_data)
        self.risk_search.textChanged.connect(self.filter_risks)
        self.filter_priority.currentTextChanged.connect(self.filter_risks)
        self.filter_status.currentTextChanged.connect(self.filter_risks)

    def add_risk(self):
        """Add a new risk"""
        try:
            # Create risk data from UI
            risk_data = {
                "description": self.risk_description.toPlainText(),
                "probability": self.probability_combo.currentText(),
                "impact": self.impact_combo.currentText(),
                "status": self.status_combo.currentText(),
                "mitigation": self.mitigation_text.toPlainText(),
                "reward_type": self.reward_type_combo.currentText(),
                "estimated_value": self.reward_value.value(),
                "reward_probability": self.reward_probability.currentText()
            }
            
            # Validate
            validation = self.validator.validate_single(risk_data)
            if not validation.valid:
                error_msg = "\n".join([
                    f"{field}: {', '.join(msgs)}" 
                    for field, msgs in validation.errors.items()
                ])
                raise ValueError(f"Validation failed:\n{error_msg}")
            
            # Create risk
            risk = RiskCreate(**risk_data)
            
            # Add to data_mux
            self.data_mux.risks.append(risk)
            
            # Update UI
            self.update_table()
            self.update_analysis()
            
            # Broadcast event
            self.event_manager.broadcast_news(
                "Risk Added",
                f"New risk '{risk.description[:30]}...' added",
                EventPriority.NORMAL
            )
            
        except Exception as e:
            logging.error(f"Error adding risk: {e}")
            self.show_error("Add Risk Error", str(e))

    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'client'):
                asyncio.run_coroutine_threadsafe(
                    self.client.close(), 
                    self.loop
                )
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            if hasattr(self, 'async_timer'):
                self.async_timer.stop()
            if hasattr(self, 'client'):
                asyncio.run_coroutine_threadsafe(
                    self.client.close(), 
                    self.loop
                )
            event.accept()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            event.accept()

    # ... rest of the original code ...

    def setup_ui_elements(self):
        """Initialize all UI elements"""
        # Create main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # Create main tabs
        self.risk_tab = QWidget()
        self.dashboard_tab = QWidget()
        self.analysis_tab = QWidget()
        self.tab_widget.addTab(self.risk_tab, "Risks")
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.analysis_tab, "Analysis")
        
        # Create search and filter widgets
        self.risk_search = QLineEdit()
        self.risk_search.setPlaceholderText("Search risks...")
        
        self.filter_priority = QComboBox()
        self.filter_priority.addItems(["All Priorities"] + [p.value for p in RiskPriority])
        
        self.filter_status = QComboBox()
        self.filter_status.addItems(["All Statuses"] + [s.value for s in RiskStatus])
        
        # Create table
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(10)
        self.risk_table.setHorizontalHeaderLabels([
            "ID", "Description", "Probability", "Impact", 
            "Priority", "Status", "Reward Type", "Value",
            "Created", "Updated"
        ])
        
   
        # Create buttons
        self.add_button = QPushButton("Add Risk")
        self.edit_button = QPushButton("Edit Risk")
        self.delete_button = QPushButton("Delete Risk")
        self.refresh_button = QPushButton("Refresh")
        
        # Create risk details widgets
        self.risk_description = QTextEdit()
        self.probability_combo = QComboBox()
        self.probability_combo.addItems([p.value for p in RiskProbability])
        
        self.impact_combo = QComboBox()
        self.impact_combo.addItems([i.value for i in ImpactSeverity])
        
        self.status_combo = QComboBox()
        self.status_combo.addItems([s.value for s in RiskStatus])
        
        self.mitigation_text = QTextEdit()
        
        # Create reward details widgets
        self.reward_type_combo = QComboBox()
        self.reward_type_combo.addItems([r.value for r in RewardType])
        self.reward_probability.addItems([p.value for p in RiskProbability])
        # Create search and filter widgets
        self.risk_search = QLineEdit()
        self.risk_search.setPlaceholderText("Search risks...")
        self.filter_priority = QComboBox()
        self.filter_status = QComboBox()
        # Add "All" options to filters
        self.filter_priority.addItem("All Priorities")
        self.filter_priority.addItems([p.value for p in RiskPriority])
        self.filter_status.addItem("All Statuses")
        self.filter_status.addItems([s.value for s in RiskStatus])
        self.reward_value = QSpinBox()
        self.reward_value.setRange(0, 1000000)
        self.reward_value.setSingleStep(1000)
        
        self.reward_probability = QComboBox()
        self.reward_probability.addItems([p.value for p in RiskProbability])
        
        # Create status indicators
        self.connection_indicator = QLabel()
        self.sync_indicator = QLabel()
        
        # Create analysis labels
        self.total_risks_label = QLabel("Total Risks: 0")
        self.high_priority_label = QLabel("High Priority: 0")
        self.open_risks_label = QLabel("Open Risks: 0")
        self.mitigated_label = QLabel("Mitigated: 0")
        self.risk_reward_ratio = QLabel("Risk-Reward Ratio: 0.0")
        self.expected_value = QLabel("Expected Value: $0.00")
        
        # Set main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def update_connection_status(self, connected: bool):
        """Update connection status indicator"""
        if connected:
            self.connection_indicator.setText("🟢 Connected")
            self.connection_indicator.setStyleSheet("color: green;")
        else:
            self.connection_indicator.setText("🔴 Disconnected")
            self.connection_indicator.setStyleSheet("color: red;")

    def update_sync_status(self, status: str):
        """Update sync status indicator"""
        status_icons = {
            "Synced": "✓",
            "Syncing": "↻",
            "Error": "⚠",
            "Not synced": "×"
        }
        icon = status_icons.get(status, "?")
        self.sync_indicator.setText(f"{icon} {status}")
        
        if status == "Synced":
            self.sync_indicator.setStyleSheet("color: green;")
        elif status == "Syncing":
            self.sync_indicator.setStyleSheet("color: blue;")
        elif status == "Error":
            self.sync_indicator.setStyleSheet("color: red;")
        else:
            self.sync_indicator.setStyleSheet("color: gray;")

    def setup_stylesheet(self):
        """Setup the widget's stylesheet"""
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #d3d3d3;
                selection-background-color: #e6e6e6;
                selection-color: black;
            }
            
            QTableWidget::item {
                padding: 5px;
            }
            
            QComboBox {
                padding: 5px;
                border: 1px solid #d3d3d3;
                border-radius: 3px;
            }
            
            QTextEdit {
                border: 1px solid #d3d3d3;
                border-radius: 3px;
                padding: 5px;
            }
            
            QPushButton {
                padding: 5px 15px;
                background-color: #f0f0f0;
                border: 1px solid #d3d3d3;
                border-radius: 3px;
            }
            
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            
            QPushButton:pressed {
                background-color: #d9d9d9;
            }
            
            QLineEdit {
                padding: 5px;
                border: 1px solid #d3d3d3;
                border-radius: 3px;
            }
            
            QLabel {
                padding: 5px;
            }
            
            QTabWidget::pane {
                border: 1px solid #d3d3d3;
                border-radius: 3px;
            }
            
            QTabBar::tab {
                padding: 8px 15px;
                background-color: #f0f0f0;
                border: 1px solid #d3d3d3;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: none;
            }
            
            QSpinBox {
                padding: 5px;
                border: 1px solid #d3d3d3;
                border-radius: 3px;
            }
            
            QGroupBox {
                margin-top: 10px;
                font-weight: bold;
                border: 1px solid #d3d3d3;
                border-radius: 3px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
    def init_ui(self):
        """Initialize the UI layout and connections"""
        # Setup risk tab layout
        risk_layout = QVBoxLayout(self.risk_tab)
        
        # Add search and filter bar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(self.risk_search)
        filter_bar.addWidget(QLabel("Priority:"))
        filter_bar.addWidget(self.filter_priority)
        filter_bar.addWidget(QLabel("Status:"))
        filter_bar.addWidget(self.filter_status)
        risk_layout.addLayout(filter_bar)
        
        # Add risk table
        risk_layout.addWidget(self.risk_table)
        
        # Add button bar
        button_bar = QHBoxLayout()
        button_bar.addWidget(self.add_button)
        button_bar.addWidget(self.edit_button)
        button_bar.addWidget(self.delete_button)
        button_bar.addWidget(self.refresh_button)
        risk_layout.addLayout(button_bar)
        
        # Add details section
        details_group = QGroupBox("Risk Details")
        details_layout = QGridLayout()
        
        # Add input fields to details
        details_layout.addWidget(QLabel("Description:"), 0, 0)
        details_layout.addWidget(self.risk_description, 0, 1)
        details_layout.addWidget(QLabel("Probability:"), 1, 0)
        details_layout.addWidget(self.probability_combo, 1, 1)
        details_layout.addWidget(QLabel("Impact:"), 2, 0)
        details_layout.addWidget(self.impact_combo, 2, 1)
        details_layout.addWidget(QLabel("Status:"), 3, 0)
        details_layout.addWidget(self.status_combo, 3, 1)
        details_layout.addWidget(QLabel("Mitigation:"), 4, 0)
        details_layout.addWidget(self.mitigation_text, 4, 1)
        
        # Add reward section
        reward_group = QGroupBox("Reward Details")
        reward_layout = QGridLayout()
        reward_layout.addWidget(QLabel("Type:"), 0, 0)
        reward_layout.addWidget(self.reward_type_combo, 0, 1)
        reward_layout.addWidget(QLabel("Value:"), 1, 0)
        reward_layout.addWidget(self.reward_value, 1, 1)
        reward_layout.addWidget(QLabel("Probability:"), 2, 0)
        reward_layout.addWidget(self.reward_probability, 2, 1)
        reward_group.setLayout(reward_layout)
        
        details_group.setLayout(details_layout)
        risk_layout.addWidget(details_group)
        risk_layout.addWidget(reward_group)
        
        # Connect signals
        self.risk_table.itemClicked.connect(self.load_risk_details)
        self.add_button.clicked.connect(self.add_risk)
        self.edit_button.clicked.connect(self.edit_risk)
        self.delete_button.clicked.connect(self.delete_risk)
        self.refresh_button.clicked.connect(self.refresh_data)
        self.risk_search.textChanged.connect(self.filter_risks)
        self.filter_priority.currentTextChanged.connect(self.filter_risks)
        self.filter_status.currentTextChanged.connect(self.filter_risks)
        
        # Setup dashboard tab
        self.setup_dashboard_tab()
        
        # Setup analysis tab
        self.setup_analysis_tab()
        
        # Add status bar indicators
        self.statusBar().addPermanentWidget(self.connection_indicator)
        self.statusBar().addPermanentWidget(self.sync_indicator)
        
        # Initial UI update
        self.update_connection_status(False)
        self.update_sync_status("Not synced")

    def setup_dashboard_tab(self):
        """Setup the dashboard tab with statistics and charts"""
        layout = QVBoxLayout(self.dashboard_tab)
        
        # Add statistics section
        stats_group = QGroupBox("Risk Statistics")
        stats_layout = QGridLayout()
        
        self.total_risks_label = QLabel("Total Risks: 0")
        self.high_priority_label = QLabel("High Priority: 0")
        self.open_risks_label = QLabel("Open Risks: 0")
        self.mitigated_label = QLabel("Mitigated: 0")
        
        stats_layout.addWidget(self.total_risks_label, 0, 0)
        stats_layout.addWidget(self.high_priority_label, 0, 1)
        stats_layout.addWidget(self.open_risks_label, 1, 0)
        stats_layout.addWidget(self.mitigated_label, 1, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

    def setup_analysis_tab(self):
        """Setup the analysis tab with risk-reward analysis"""
        layout = QVBoxLayout(self.analysis_tab)
        
        analysis_group = QGroupBox("Risk-Reward Analysis")
        analysis_layout = QVBoxLayout()
        
        self.risk_reward_ratio = QLabel("Risk-Reward Ratio: 0.0")
        self.expected_value = QLabel("Expected Value: $0.00")
        
        analysis_layout.addWidget(self.risk_reward_ratio)
        analysis_layout.addWidget(self.expected_value)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)

    def load_risk_details(self, item):
        """Load selected risk details into the editor"""
        row = item.row()
        risk_id = int(self.risk_table.item(row, 0).text())
        
        try:
            risk = self.get_risk_by_id(risk_id)
            if not risk:
                return
            
            # Update UI elements with risk details
            self.description_text.setText(risk.description)
            self.probability_combo.setCurrentText(risk.probability.value)
            self.impact_combo.setCurrentText(risk.impact.value)
            self.status_combo.setCurrentText(risk.status.value)
            self.mitigation_text.setText(risk.mitigation)
            
            # Enable edit/delete buttons
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            
        except Exception as e:
            logging.error(f"Error loading risk details: {e}")
            self.show_error("Failed to load risk details")

    def get_risk_by_id(self, risk_id: int):
        """Retrieve risk by ID from local cache or server"""
        try:
            if hasattr(self, 'risks_cache'):
                return next((r for r in self.risks_cache if r.id == risk_id), None)
            return None
        except Exception as e:
            logging.error(f"Error retrieving risk: {e}")
            return None

    def add_risk(self):
        """Open dialog to add new risk"""
        try:
            dialog = RiskEditorDialog(parent=self)
            if dialog.exec():
                risk_data = dialog.get_risk_data()
                
                # Validate risk data
                validation = self.validator.validate_single(risk_data)
                if not validation.valid:
                    self.show_error("Invalid risk data", validation.errors)
                    return
                
                # Create new risk
                new_risk = self.create_risk(risk_data)
                if new_risk:
                    self.refresh_data()
                    self.show_info("Risk added successfully")
                
        except Exception as e:
            logging.error(f"Error adding risk: {e}")
            self.show_error("Failed to add risk")

    def edit_risk(self):
        """Edit selected risk"""
        try:
            current_row = self.risk_table.currentRow()
            if current_row < 0:
                return
                
            risk_id = int(self.risk_table.item(current_row, 0).text())
            risk = self.get_risk_by_id(risk_id)
            if not risk:
                return
                
            dialog = RiskEditorDialog(risk_data=risk, parent=self)
            if dialog.exec():
                updated_data = dialog.get_risk_data()
                
                # Validate updated data
                validation = self.validator.validate_single(updated_data)
                if not validation.valid:
                    self.show_error("Invalid risk data", validation.errors)
                    return
                
                # Update risk
                if self.update_risk(risk_id, updated_data):
                    self.refresh_data()
                    self.show_info("Risk updated successfully")
                
        except Exception as e:
            logging.error(f"Error editing risk: {e}")
            self.show_error("Failed to edit risk")

    def delete_risk(self):
        """Delete selected risk"""
        try:
            current_row = self.risk_table.currentRow()
            if current_row < 0:
                return
                
            risk_id = int(self.risk_table.item(current_row, 0).text())
            
            reply = QMessageBox.question(
                self, "Delete Risk",
                "Are you sure you want to delete this risk?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.delete_risk_by_id(risk_id):
                    self.refresh_data()
                    self.show_info("Risk deleted successfully")
                
        except Exception as e:
            logging.error(f"Error deleting risk: {e}")
            self.show_error("Failed to delete risk")

    def refresh_data(self):
        """Refresh risk data from server"""
        try:
            self.load_data()
            self.filter_risks()  # Apply current filters
            self.show_info("Data refreshed successfully")
        except Exception as e:
            logging.error(f"Error refreshing data: {e}")
            self.show_error("Failed to refresh data")

    def filter_risks(self):
        """Apply filters to risk table"""
        try:
            search_text = self.risk_search.text().lower()
            priority_filter = self.filter_priority.currentText()
            status_filter = self.filter_status.currentText()
            
            self.risk_table.setRowCount(0)
            
            if not hasattr(self, 'risks_cache'):
                return
                
            for risk in self.risks_cache:
                if (
                    (search_text in risk.description.lower()) and
                    (priority_filter == "All Priorities" or risk.priority == priority_filter) and
                    (status_filter == "All Statuses" or risk.status.value == status_filter)
                ):
                    self.add_risk_to_table(risk)
                    
        except Exception as e:
            logging.error(f"Error filtering risks: {e}")
            self.show_error("Failed to apply filters")

    def add_risk_to_table(self, risk):
        """Add a risk to the table widget"""
        row = self.risk_table.rowCount()
        self.risk_table.insertRow(row)
        
        self.risk_table.setItem(row, 0, QTableWidgetItem(str(risk.id)))
        self.risk_table.setItem(row, 1, QTableWidgetItem(risk.description))
        self.risk_table.setItem(row, 2, QTableWidgetItem(risk.priority))
        self.risk_table.setItem(row, 3, QTableWidgetItem(risk.status.value))
        self.risk_table.setItem(row, 4, QTableWidgetItem(
            risk.last_updated.strftime("%Y-%m-%d %H:%M")
        ))
        self.risk_table.setItem(row, 5, QTableWidgetItem(risk.owner))

    def show_error(self, message, details=None):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
        if details:
            logging.error(f"Error details: {details}")

    def show_info(self, message):
        """Show info message"""
        self.statusBar().showMessage(message, 3000)  # Show for 3 seconds

    def _on_risk_created(self, risk_id: int):
        """Handle newly created risk"""
        try:
            # Fetch the new risk from repository
            risk = self.repository.get_by_id(risk_id)
            if risk:
                self.risks_cache.append(risk)
                self.add_risk_to_table(risk)
                self.show_info(f"Risk {risk_id} created successfully")
            
            # Update project dashboard if available
            if self.cccore and hasattr(self.cccore, 'project_dashboard'):
                self.cccore.project_dashboard.update_risk_section()
                
        except Exception as e:
            logging.error(f"Error handling new risk: {e}")
            self.show_error("Failed to process new risk")

    def _on_risk_deleted(self, risk_id: int):
        """Handle deleted risk"""
        try:
            # Remove from cache
            self.risks_cache = [r for r in self.risks_cache if r.id != risk_id]
            
            # Remove from table
            for row in range(self.risk_table.rowCount()):
                if int(self.risk_table.item(row, 0).text()) == risk_id:
                    self.risk_table.removeRow(row)
                    break
                    
            self.show_info(f"Risk {risk_id} deleted successfully")
            
            # Update project dashboard if available
            if self.cccore and hasattr(self.cccore, 'project_dashboard'):
                self.cccore.project_dashboard.update_risk_section()
                
        except Exception as e:
            logging.error(f"Error handling risk deletion: {e}")
            self.show_error("Failed to process risk deletion")

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    from riskkit.config import ConfigManager
    
    app = QApplication(sys.argv)
    
    # Create minimal dependencies
    config_manager = ConfigManager()
        
    notification_manager = NotificationManager()
    
    # Create and show window
    window = RiskManager(
        config_manager=config_manager,
        notification_manager=notification_manager
    )
    window.show()
    
    # Run application
    sys.exit(app.exec())

