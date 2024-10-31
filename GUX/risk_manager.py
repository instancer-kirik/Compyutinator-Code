from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, 
                            QLabel, QComboBox, QTextEdit, QSpinBox, QFileDialog, QInputDialog, QMessageBox, QTabWidget, QGroupBox, QVBoxLayout, QGridLayout, QWidget, QDialog, QLineEdit, QRadioButton)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush, QKeySequence, QShortcut
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from riskkit.client import RiskkitClient, ApiConfig
import asyncio
import os

class ConflictResolutionDialog(QDialog):
    def __init__(self, conflicts: Dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resolve Conflicts")
        self.conflicts = conflicts
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        for field, values in self.conflicts.items():
            group = QGroupBox(f"Conflict in {field}")
            group_layout = QVBoxLayout()
            
            local_radio = QRadioButton(f"Local: {values['local']}")
            remote_radio = QRadioButton(f"Remote: {values['remote']}")
            
            group_layout.addWidget(local_radio)
            group_layout.addWidget(remote_radio)
            group.setLayout(group_layout)
            layout.addWidget(group)
        
        buttons = QHBoxLayout()
        accept = QPushButton("Accept Selected")
        cancel = QPushButton("Cancel")
        
        buttons.addWidget(accept)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        
        accept.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        self.status_combo.currentTextChanged.connect(self.validate_status_transition)

class RiskManager(QMainWindow):
    # Move constants to class level
    RISK_WEIGHTS = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    REWARD_WEIGHTS = {"Low": 1, "Medium": 2, "High": 3}
    PROBABILITY_WEIGHTS = {"Low": 0.3, "Medium": 0.5, "High": 0.7}
    
    RATIO_THRESHOLDS = {
        2.0: ("Highly Favorable - Proceed", "green"),
        1.0: ("Favorable - Proceed with caution", "lightgreen"),
        0.5: ("Marginal - Additional mitigation recommended", "yellow"),
        0.0: ("Unfavorable - Reconsider or enhance rewards", "red")
    }

    # Add color constants
    COLORS = {
        "Critical": QColor("#FF4444"),  # Red
        "High": QColor("#FFA500"),      # Orange
        "Medium": QColor("#FFD700"),    # Yellow
        "Low": QColor("#90EE90"),       # Light Green
        "Open": QColor("#FFE4E1"),      # Light Red
        "Mitigated": QColor("#E0FFFF"), # Light Cyan
        "Closed": QColor("#98FB98"),     # Pale Green
        # Add reward colors
        "High Reward": QColor("#32CD32"),    # Lime Green
        "Medium Reward": QColor("#98FB98"),   # Pale Green
        "Low Reward": QColor("#E0FFC0"),     # Light Mint
        "Opportunity": QColor("#87CEEB"),     # Sky Blue
        "Cost Saving": QColor("#DDA0DD"),    # Plum
        "Revenue": QColor("#FFD700")         # Gold
    }

    # Rename DEFAULT_PORTFOLIO to SAMPLE_RISKS
    SAMPLE_RISKS = [
        {
            "id": 1,
            "description": "Server Infrastructure Upgrade",
            "probability": "Medium",
            "impact": "High",
            "priority": "High",
            "status": "Open",
            "mitigation": "Planned phased rollout with fallback options",
            "reward_type": "Cost Saving",
            "estimated_value": 50000,
            "reward_probability": "High",
            "date_created": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "id": 2,
            "description": "New Market Entry",
            "probability": "High",
            "impact": "Critical",
            "priority": "Critical",
            "status": "Open",
            "mitigation": "Detailed market research and phased entry strategy",
            "reward_type": "Revenue",
            "estimated_value": 200000,
            "reward_probability": "Medium",
            "date_created": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "id": 3,
            "description": "Legacy System Migration",
            "probability": "Medium",
            "impact": "Medium",
            "priority": "Medium",
            "status": "Mitigated",
            "mitigation": "Comprehensive testing and backup procedures",
            "reward_type": "Cost Saving",
            "estimated_value": 30000,
            "reward_probability": "High",
            "date_created": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
    ]

    # Group related methods into sections with comments
    
    # 1. Initialization and Setup
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Risk Management System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize UI elements first
        self.setup_ui_elements()
        
        # Set stylesheet after elements are created
        self.setup_stylesheet()
        
        # Initialize risk list and history
        self.risks = []
        self.risk_history = []
        
        # Initialize UI
        self.init_ui()
        self.load_risks()
        
        # Setup additional features
        self.setup_shortcuts()
        self.setup_status_bar()

        self.setup_client()
        self.connect_signals()

    def setup_ui_elements(self):
        """Initialize all UI elements before creating tabs"""
        # Risk Table
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(6)
        self.risk_table.setHorizontalHeaderLabels([
            "Risk ID", "Description", "Probability", 
            "Impact", "Priority", "Status"
        ])
        
        # Buttons
        self.add_button = QPushButton("Add Risk")
        self.edit_button = QPushButton("Edit Risk")
        self.delete_button = QPushButton("Delete Risk")
        self.save_button = QPushButton("Save Changes")
        
        # Combo boxes
        self.probability_combo = QComboBox()
        self.probability_combo.addItems(["Low", "Medium", "High", "Critical"])
        
        self.impact_combo = QComboBox()
        self.impact_combo.addItems(["Low", "Medium", "High", "Critical"])
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Open", "Mitigated", "Closed"])
        
        # Text fields
        self.risk_description = QTextEdit()
        self.mitigation_text = QTextEdit()
        
        # Search and filters
        self.risk_search = QTextEdit()
        self.risk_search.setMaximumHeight(30)
        self.filter_priority = QComboBox()
        self.filter_priority.addItems(["All Priorities", "Low", "Medium", "High", "Critical"])
        self.filter_status = QComboBox()
        self.filter_status.addItems(["All Statuses", "Open", "Mitigated", "Closed"])
        
        # Recent activities table
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(3)
        self.recent_table.setHorizontalHeaderLabels(["Date", "Risk ID", "Action"])
        
        # Labels for dashboard
        self.total_risks_label = QLabel("Total Risks: 0")
        self.high_risks_label = QLabel("High Priority: 0")
        self.medium_risks_label = QLabel("Medium Priority: 0")
        self.low_risks_label = QLabel("Low Priority: 0")
        
        # Analysis labels
        self.risk_reward_ratio = QLabel("Risk-Reward Ratio: N/A")
        self.expected_value = QLabel("Expected Value: $0")
        self.recommendation = QLabel("Recommendation: Need more data")
        
        # Reward elements
        self.reward_type_combo = QComboBox()
        self.reward_type_combo.addItems([
            "Opportunity", "Cost Saving", "Revenue", 
            "Market Share", "Competitive Advantage"
        ])
        
        self.reward_value = QSpinBox()
        self.reward_value.setRange(0, 1000000)
        self.reward_value.setSuffix(" $")
        
        self.reward_probability = QComboBox()
        self.reward_probability.addItems(["Low", "Medium", "High"])

    def setup_stylesheet(self):
        """Set up the application stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f0f;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTableWidget {
                background-color: #0f0f0f;
                gridline-color: #d0d0d0;
                color: white;
            }
            QTableWidget::item:selected {
                background-color: #bde9ba;
            }
            QLabel {
                font-weight: bold;
                color: white;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #999;
                border-radius: 3px;
                color: white;
                background-color: #2d2d2d;
            }
            QTextEdit {
                border: 1px solid #999;
                border-radius: 3px;
                color: white;
                background-color: #2d2d2d;
            }
            QSpinBox {
                color: white;
                background-color: #2d2d2d;
                border: 1px solid #999;
                border-radius: 3px;
            }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background: #0f0f0f;
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #fff;
                padding: 8px 20px;
                border: 1px solid #444;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
            }
            QTabBar::tab:hover {
                background: #45a049;
            }
        """)

        # Create individual tabs
        dashboard_tab = self.create_dashboard_tab()
        risk_registry_tab = self.create_risk_registry_tab()
        assessment_tab = self.create_assessment_tab()
        reports_tab = self.create_reports_tab()

        # Add tabs to widget
        tabs.addTab(dashboard_tab, "Dashboard")
        tabs.addTab(risk_registry_tab, "Risk Registry")
        tabs.addTab(assessment_tab, "Risk Assessment")
        tabs.addTab(reports_tab, "Reports")

        main_layout.addWidget(tabs)

    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # 1. Summary Cards (Smaller, in a row)
        stats_group = QGroupBox("Quick Stats")
        stats_group.setFixedHeight(150)
        stats_layout = QHBoxLayout()
        
        def create_stat_card(title, value, color):
            card = QWidget()
            card.setFixedWidth(180)
            card.setStyleSheet(f"""
                QWidget {{
                    background-color: {color};
                    border-radius: 8px;
                    padding: 5px;
                }}
                QLabel {{
                    color: white;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(2)
            title_label = QLabel(title)
            value_label = QLabel(str(value))
            value_label.setStyleSheet("font-size: 18px; font-weight: bold;")
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            return card
        
        # Add cards with safe calculations
        total_risks = len(self.risks)
        high_priority = sum(1 for risk in self.risks if risk["priority"] in ["Critical", "High"])
        open_risks = sum(1 for risk in self.risks if risk["status"] == "Open")
        mitigated = sum(1 for risk in self.risks if risk["status"] == "Mitigated")
        
        stats_layout.addWidget(create_stat_card("Total Risks", total_risks, "#2196F3"))
        stats_layout.addWidget(create_stat_card("High Priority", high_priority, "#f44336"))
        stats_layout.addWidget(create_stat_card("Open Risks", open_risks, "#ff9800"))
        stats_layout.addWidget(create_stat_card("Mitigated", mitigated, "#4CAF50"))
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group, 0, 0, 1, 2)
        
        # 2. Recent Activities (Left side)
        recent_group = QGroupBox("Recent Activities")
        recent_layout = QVBoxLayout()
        self.recent_table.setMaximumHeight(200)
        recent_layout.addWidget(self.recent_table)
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group, 1, 0)
        
        # 3. Risk Distribution Chart (Right side)
        chart_group = QGroupBox("Risk Distribution")
        chart_layout = QVBoxLayout()
        chart_widget = self.create_risk_distribution_chart()
        chart_layout.addWidget(chart_widget)
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group, 1, 1)
        
        # 4. Quick Actions (Bottom left)
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout()
        
        add_risk_btn = QPushButton("➕ Add New Risk")
        import_btn = QPushButton("📥 Import Portfolio")  # Add import button
        export_btn = QPushButton("📊 Export Report")
        filter_high_btn = QPushButton("⚠️ Show High Priority")
        
        for btn in [add_risk_btn, import_btn, export_btn, filter_high_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    margin: 2px;
                }
            """)
            actions_layout.addWidget(btn)
        
        add_risk_btn.clicked.connect(self.add_risk)
        import_btn.clicked.connect(self.import_risk_registry)  # Connect import button
        export_btn.clicked.connect(self.export_to_csv)
        filter_high_btn.clicked.connect(lambda: self.filter_priority.setCurrentText("High"))
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group, 2, 0)
        
        # 5. Key Metrics (Bottom right) with safe calculations
        metrics_group = QGroupBox("Key Metrics")
        metrics_layout = QGridLayout()
        
        # Safe calculations with default values
        total_value = sum(risk.get("estimated_value", 0) for risk in self.risks)
        open_value = sum(risk.get("estimated_value", 0) for risk in self.risks 
                        if risk.get("status") == "Open")
        
        # Safe average calculation
        if self.risks:
            avg_ratio = sum(risk.get("risk_reward_ratio", 0) for risk in self.risks) / len(self.risks)
            mitigation_rate = (len(self.risks) - open_risks) / len(self.risks) * 100
        else:
            avg_ratio = 0
            mitigation_rate = 0
        
        metrics = [
            ("Total Portfolio Value:", f"${total_value:,.2f}"),
            ("Open Risk Value:", f"${open_value:,.2f}"),
            ("Avg Risk-Reward Ratio:", f"{avg_ratio:.2f}"),
            ("Risk Mitigation Rate:", f"{mitigation_rate:.1f}%")
        ]
        
        for i, (label, value) in enumerate(metrics):
            metrics_layout.addWidget(QLabel(label), i, 0)
            value_label = QLabel(value)
            value_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            metrics_layout.addWidget(value_label, i, 1)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group, 2, 1)
        
        # Add State Machine Editor button
        state_machine_btn = QPushButton("📊 Edit State Machine")
        state_machine_btn.clicked.connect(self.show_state_machine_editor)
        actions_layout.addWidget(state_machine_btn)
        
        return tab

    def create_risk_distribution_chart(self):
        chart = QWidget()
        chart.setMinimumHeight(200)
        chart.setStyleSheet("background-color: #2d2d2d; border-radius: 5px;")
        
        # Create a simple visual representation using labels
        layout = QVBoxLayout(chart)
        
        if not self.risks:
            placeholder = QLabel("No risks to display")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: white;")
            layout.addWidget(placeholder)
            return chart
        
        # Calculate distribution
        priority_counts = {
            "Critical": sum(1 for r in self.risks if r["priority"] == "Critical"),
            "High": sum(1 for r in self.risks if r["priority"] == "High"),
            "Medium": sum(1 for r in self.risks if r["priority"] == "Medium"),
            "Low": sum(1 for r in self.risks if r["priority"] == "Low")
        }
        
        # Create simple bar representation
        for priority, count in priority_counts.items():
            bar = QWidget()
            bar_layout = QHBoxLayout(bar)
            
            label = QLabel(f"{priority}: {count}")
            label.setStyleSheet("color: white; min-width: 100px;")
            bar_layout.addWidget(label)
            
            bar_visual = QWidget()
            width = int((count / len(self.risks)) * 200) if self.risks else 0
            bar_visual.setFixedSize(width, 20)
            bar_visual.setStyleSheet(f"""
                background-color: {self.COLORS[priority].name()};
                border-radius: 3px;
            """)
            bar_layout.addWidget(bar_visual)
            bar_layout.addStretch()
            
            layout.addWidget(bar)
        
        return chart

    def create_risk_registry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Search and Filter Section
        filter_group = QGroupBox("Search & Filter")
        filter_group.setStyleSheet("QGroupBox { color: white; }")
        filter_layout = QHBoxLayout()

        # Search box with icon
        search_layout = QHBoxLayout()
        self.risk_search = QLineEdit()  # Change to QLineEdit
        self.risk_search.setPlaceholderText("🔍 Search risks...")
        self.risk_search.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 15px;
                padding: 5px 10px 5px 30px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
        
        search_layout.addWidget(self.risk_search)
        search_layout.addStretch()

        self.filter_priority.addItems(["All Priorities", "Low", "Medium", "High", "Critical"])
        self.filter_priority.setStyleSheet("color: white;")

        self.filter_status.addItems(["All Statuses", "Open", "Mitigated", "Closed"])
        self.filter_status.setStyleSheet("color: white;")

        filter_layout.addLayout(search_layout)
        filter_layout.addWidget(self.filter_priority)
        filter_layout.addWidget(self.filter_status)
        filter_group.setLayout(filter_layout)

        # Risk Table (reuse existing table)
        self.risk_table.setStyleSheet("color: white;")

        # Button Group
        button_group = QHBoxLayout()
        for button in [self.add_button, self.edit_button, self.delete_button]:
            button_group.addWidget(button)

        layout.addWidget(filter_group)
        layout.addWidget(self.risk_table)
        layout.addLayout(button_group)

        return tab

    def create_assessment_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)

        # Risk Assessment
        risk_group = QGroupBox("Risk Assessment")
        risk_group.setStyleSheet("QGroupBox { color: white; }")
        risk_layout = QGridLayout()

        # Existing risk fields...

        # Reward Assessment
        reward_group = QGroupBox("Reward Assessment")
        reward_group.setStyleSheet("QGroupBox { color: white; }")
        reward_layout = QGridLayout()

        self.reward_type_combo.addItems([
            "Opportunity", "Cost Saving", "Revenue", 
            "Market Share", "Competitive Advantage"
        ])

        self.reward_value.setRange(0, 1000000)
        self.reward_value.setSuffix(" $")

        self.reward_probability.addItems(["Low", "Medium", "High"])

        reward_layout.addWidget(QLabel("Reward Type:"), 0, 0)
        reward_layout.addWidget(self.reward_type_combo, 0, 1)
        reward_layout.addWidget(QLabel("Estimated Value:"), 1, 0)
        reward_layout.addWidget(self.reward_value, 1, 1)
        reward_layout.addWidget(QLabel("Probability:"), 2, 0)
        reward_layout.addWidget(self.reward_probability, 2, 1)

        # Risk-Reward Analysis
        analysis_group = QGroupBox("Risk-Reward Analysis")
        analysis_group.setStyleSheet("QGroupBox { color: white; }")
        analysis_layout = QGridLayout()

        self.risk_reward_ratio.setText("Risk-Reward Ratio: N/A")
        self.expected_value.setText("Expected Value: $0")
        self.recommendation.setText("Recommendation: Need more data")

        analysis_layout.addWidget(self.risk_reward_ratio, 0, 0)
        analysis_layout.addWidget(self.expected_value, 1, 0)
        analysis_layout.addWidget(self.recommendation, 2, 0)

        # Connect signals for real-time updates
        self.reward_type_combo.currentTextChanged.connect(self.update_analysis)
        self.reward_value.valueChanged.connect(self.update_analysis)
        self.reward_probability.currentTextChanged.connect(self.update_analysis)
        
        # Add reward colors to combo boxes
        self.reward_type_combo.currentTextChanged.connect(self.update_combo_colors)
        self.reward_probability.currentTextChanged.connect(self.update_combo_colors)

        # Add all groups to main layout
        layout.addWidget(risk_group, 0, 0)
        layout.addWidget(reward_group, 0, 1)
        layout.addWidget(analysis_group, 1, 0, 1, 2)

        return tab

    def create_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Report Options
        options_group = QGroupBox("Report Options")
        options_group.setStyleSheet("QGroupBox { color: white; }")
        options_layout = QGridLayout()

        report_types = QComboBox()
        report_types.addItems([
            "Risk Summary Report",
            "High Priority Risks",
            "Open Risks Report",
            "Mitigation Status Report"
        ])
        report_types.setStyleSheet("color: white;")

        generate_button = QPushButton("Generate Report")
        export_button = QPushButton("Export to CSV")

        options_layout.addWidget(QLabel("Report Type:"), 0, 0)
        options_layout.addWidget(report_types, 0, 1)
        options_layout.addWidget(generate_button, 1, 0)
        options_layout.addWidget(export_button, 1, 1)

        options_group.setLayout(options_layout)

        # Report Preview
        preview_group = QGroupBox("Report Preview")
        preview_group.setStyleSheet("QGroupBox { color: white; }")
        preview_layout = QVBoxLayout()
        
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setStyleSheet("color: white;")
        preview_layout.addWidget(preview_text)
        preview_group.setLayout(preview_layout)

        layout.addWidget(options_group)
        layout.addWidget(preview_group)

        return tab

    def calculate_priority(self, probability, impact):
        priority_matrix = {
            ("High", "High"): "Critical",
            ("High", "Medium"): "High",
            ("High", "Low"): "Medium",
            ("Medium", "High"): "High",
            ("Medium", "Medium"): "Medium",
            ("Medium", "Low"): "Low",
            ("Low", "High"): "Medium",
            ("Low", "Medium"): "Low",
            ("Low", "Low"): "Low"
        }
        return priority_matrix.get((probability, impact), "Medium")

    def add_risk(self):
        # Create input dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Risk")
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: white; }
            QLineEdit, QTextEdit { 
                background-color: #2d2d2d; 
                color: white;
                border: 1px solid #3d3d3d;
                padding: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 15px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QGridLayout(dialog)
        
        # Add fields
        fields = {
            "Description": QTextEdit(),
            "Probability": QComboBox(),
            "Impact": QComboBox(),
            "Status": QComboBox(),
            "Mitigation": QTextEdit(),
            "Reward Type": QComboBox(),
            "Estimated Value": QSpinBox(),
            "Reward Probability": QComboBox()
        }
        
        # Configure fields
        fields["Probability"].addItems(["Low", "Medium", "High", "Critical"])
        fields["Impact"].addItems(["Low", "Medium", "High", "Critical"])
        fields["Status"].addItems(["Open", "Mitigated", "Closed"])
        fields["Reward Type"].addItems(["Opportunity", "Cost Saving", "Revenue"])
        fields["Reward Probability"].addItems(["Low", "Medium", "High"])
        fields["Estimated Value"].setRange(0, 1000000)
        fields["Estimated Value"].setSuffix(" $")
        
        # Add fields to layout
        row = 0
        for label, widget in fields.items():
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(widget, row, 1)
            row += 1
        
        # Add buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, row, 0, 1, 2)
        
        # Connect buttons
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            risk_id = len(self.risks) + 1
            new_risk = {
                "id": risk_id,
                "description": fields["Description"].toPlainText(),
                "probability": fields["Probability"].currentText(),
                "impact": fields["Impact"].currentText(),
                "priority": self.calculate_priority(
                    fields["Probability"].currentText(),
                    fields["Impact"].currentText()
                ),
                "status": fields["Status"].currentText(),
                "mitigation": fields["Mitigation"].toPlainText(),
                "reward_type": fields["Reward Type"].currentText(),
                "estimated_value": fields["Estimated Value"].value(),
                "reward_probability": fields["Reward Probability"].currentText(),
                "date_created": datetime.now().strftime("%Y-%m-%d"),
                "last_updated": datetime.now().strftime("%Y-%m-%d")
            }
            
            self.risks.append(new_risk)
            self.update_table()
            self.save_risks()
            self.add_to_history(risk_id, "Risk Added")
            
            # Select the new row
            self.risk_table.selectRow(len(self.risks) - 1)
            self.load_risk_details(self.risk_table.item(len(self.risks) - 1, 0))

    def edit_risk(self):
        current_row = self.risk_table.currentRow()
        if current_row >= 0:
            risk = self.risks[current_row]
            new_status = self.status_combo.currentText()
            
            # Prepare context for state transition
            context = {
                "owner": risk.get("owner", ""),
                "mitigation": self.mitigation_text.toPlainText(),
                "resources": risk.get("resources", []),
                "approved_by": risk.get("approved_by", ""),
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "completion_date": datetime.now().strftime("%Y-%m-%d"),
                "acceptance_rationale": risk.get("acceptance_rationale", ""),
                "closure_notes": risk.get("closure_notes", "")
            }

            # Check if state transition is valid
            risk_obj = Risk.from_dict(risk)
            if new_status != risk["status"]:
                if not risk_obj.can_transition_to(new_status, context):
                    QMessageBox.warning(
                        self, 
                        "Invalid Transition",
                        f"Cannot transition from {risk['status']} to {new_status}"
                    )
                    self.status_combo.setCurrentText(risk["status"])
                    return
                
                if not risk_obj.transition_to(new_status, context):
                    QMessageBox.warning(
                        self, 
                        "Transition Failed",
                        "Failed to transition risk status"
                    )
                    return

            # Update other risk fields
            risk.update({
                "description": self.risk_description.toPlainText(),
                "probability": self.probability_combo.currentText(),
                "impact": self.impact_combo.currentText(),
                "priority": self.calculate_priority(
                    self.probability_combo.currentText(),
                    self.impact_combo.currentText()
                ),
                "status": new_status,
                "mitigation": self.mitigation_text.toPlainText(),
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "reward_type": self.reward_type_combo.currentText(),
                "estimated_value": self.reward_value.value(),
                "reward_probability": self.reward_probability.currentText(),
                "risk_reward_ratio": self.calculate_risk_reward_ratio(risk)
            })

            self.update_table()
            self.update_analysis()
            self.save_risks()
            self.update_combo_colors()
            self.add_to_history(risk["id"], f"Updated status to {new_status}")
            QMessageBox.information(self, "Success", "Risk updated successfully!")

    def update_combo_colors(self):
        """Update the background colors of combo boxes based on selection"""
        # Fix syntax error by properly formatting lines
        prob_color = self.COLORS.get(self.probability_combo.currentText(), QColor("white"))
        self.probability_combo.setStyleSheet(f"background-color: {prob_color.name()}")
        
        impact_color = self.COLORS.get(self.impact_combo.currentText(), QColor("white"))
        self.impact_combo.setStyleSheet(f"background-color: {impact_color.name()}")
        
        # Status combo
        status_color = self.COLORS.get(self.status_combo.currentText(), QColor("white"))
        self.status_combo.setStyleSheet(f"background-color: {status_color.name()}")

        # Add reward combos
        reward_type_color = self.COLORS.get(self.reward_type_combo.currentText(), QColor("white"))
        self.reward_type_combo.setStyleSheet(f"background-color: {reward_type_color.name()}")
        
        reward_prob_color = self.COLORS.get(
            f"{self.reward_probability.currentText()} Reward", 
            QColor("white")
        )
        self.reward_probability.setStyleSheet(f"background-color: {reward_prob_color.name()}")

    def delete_risk(self):
        current_row = self.risk_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "Confirm Deletion",
                "Are you sure you want to delete this risk?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.risks.pop(current_row)
                self.update_table()
                self.save_risks()

    def load_risk_details(self, item):
        row = item.row()
        risk = self.risks[row]
        
        self.risk_description.setText(risk["description"])
        self.probability_combo.setCurrentText(risk["probability"])
        self.impact_combo.setCurrentText(risk["impact"])
        self.status_combo.setCurrentText(risk["status"])
        self.mitigation_text.setText(risk.get("mitigation", ""))

    def update_table(self):
        self.risk_table.setRowCount(len(self.risks))
        for row, risk in enumerate(self.risks):
            # Create and style items
            id_item = QTableWidgetItem(str(risk["id"]))
            desc_item = QTableWidgetItem(risk["description"])
            prob_item = QTableWidgetItem(risk["probability"])
            impact_item = QTableWidgetItem(risk["impact"])
            priority_item = QTableWidgetItem(risk["priority"])
            status_item = QTableWidgetItem(risk["status"])

            # Center align text
            for item in [id_item, prob_item, impact_item, priority_item, status_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Set colors based on priority
            priority_color = self.COLORS.get(risk["priority"], QColor("white"))
            priority_item.setBackground(QBrush(priority_color))

            # Set colors based on status
            status_color = self.COLORS.get(risk["status"], QColor("white"))
            status_item.setBackground(QBrush(status_color))

            # Set probability color
            prob_color = {
                "High": self.COLORS["High"],
                "Medium": self.COLORS["Medium"],
                "Low": self.COLORS["Low"]
            }.get(risk["probability"], QColor("white"))
            prob_item.setBackground(QBrush(prob_color))

            # Set impact color
            impact_color = {
                "High": self.COLORS["High"],
                "Medium": self.COLORS["Medium"],
                "Low": self.COLORS["Low"]
            }.get(risk["impact"], QColor("white"))
            impact_item.setBackground(QBrush(impact_color))

            # Set items in table
            self.risk_table.setItem(row, 0, id_item)
            self.risk_table.setItem(row, 1, desc_item)
            self.risk_table.setItem(row, 2, prob_item)
            self.risk_table.setItem(row, 3, impact_item)
            self.risk_table.setItem(row, 4, priority_item)
            self.risk_table.setItem(row, 5, status_item)

        # Adjust column widths
        self.risk_table.setColumnWidth(0, 70)  # ID
        self.risk_table.setColumnWidth(1, 300) # Description
        self.risk_table.setColumnWidth(2, 100) # Probability
        self.risk_table.setColumnWidth(3, 100) # Impact
        self.risk_table.setColumnWidth(4, 100) # Priority
        self.risk_table.setColumnWidth(5, 100) # Status

    def save_risks(self):
        try:
            data = {
                "risks": self.risks,
                "history": self.risk_history,
                "last_updated": datetime.now().isoformat()
            }
            with open('risk_database.json', 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save risks: {str(e)}")

    def load_risks(self):
        """Load risks from file or initialize with default portfolio"""
        try:
            with open('risk_database.json', 'r') as f:
                data = json.load(f)
                self.risks = data.get("risks", [])
                self.risk_history = data.get("history", [])
        except FileNotFoundError:
            # Initialize with default portfolio
            self.risks = self.SAMPLE_RISKS.copy()
            self.risk_history = [
                {
                    "date": datetime.now().isoformat(),
                    "risk_id": risk["id"],
                    "action": "Imported from default portfolio",
                    "user": "system"
                }
                for risk in self.risks
            ]
            self.save_risks()  # Save the default portfolio
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load risks: {str(e)}")
            self.risks = []
            self.risk_history = []
        
        self.update_table()
        self.update_dashboard()

    def save_assessment(self):
        if not self.risk_table.currentRow() >= 0:
            QMessageBox.warning(self, "Warning", "Please select a risk to update")
            return
        self.edit_risk()

    def setup_search_filters(self):
        self.risk_search.textChanged.connect(self.filter_risks)
        self.filter_priority.currentTextChanged.connect(self.filter_risks)
        self.filter_status.currentTextChanged.connect(self.filter_risks)

    def filter_risks(self):
        search_text = self.risk_search.toPlainText().lower()
        priority_filter = self.filter_priority.currentText()
        status_filter = self.filter_status.currentText()

        for row in range(self.risk_table.rowCount()):
            show_row = True
            
            # Text search
            if search_text:
                description = self.risk_table.item(row, 1).text().lower()
                if search_text not in description:
                    show_row = False
            
            # Priority filter
            if priority_filter != "All Priorities":
                priority = self.risk_table.item(row, 4).text()
                if priority != priority_filter:
                    show_row = False
            
            # Status filter
            if status_filter != "All Statuses":
                status = self.risk_table.item(row, 5).text()
                if status != status_filter:
                    show_row = False
            
            self.risk_table.setRowHidden(row, not show_row)

    def add_to_history(self, risk_id, action):
        history_entry = {
            "date": datetime.now().isoformat(),
            "risk_id": risk_id,
            "action": action,
            "user": "system"  # Could be expanded with user authentication
        }
        self.risk_history.append(history_entry)
        self.update_recent_activities()

    def update_recent_activities(self):
        recent = sorted(self.risk_history, key=lambda x: x["date"], reverse=True)[:5]
        self.recent_table.setRowCount(len(recent))
        
        for row, entry in enumerate(recent):
            date = QTableWidgetItem(entry["date"].split("T")[0])
            risk_id = QTableWidgetItem(str(entry["risk_id"]))
            action = QTableWidgetItem(entry["action"])
            
            self.recent_table.setItem(row, 0, date)
            self.recent_table.setItem(row, 1, risk_id)
            self.recent_table.setItem(row, 2, action)

    def export_to_csv(self):
        try:
            with open('risk_export.csv', 'w') as f:
                headers = [
                    "Risk ID", "Description", "Probability", "Impact", 
                    "Priority", "Status", "Mitigation", 
                    "Reward Type", "Estimated Value", "Reward Probability",
                    "Risk-Reward Ratio", "Created", "Updated"
                ]
                f.write(",".join(headers) + "\n")
                
                for risk in self.risks:
                    row = [
                        str(risk["id"]),
                        risk["description"].replace(",", ";"),
                        risk["probability"],
                        risk["impact"],
                        risk["priority"],
                        risk["status"],
                        risk["mitigation"].replace(",", ";"),
                        risk["reward_type"],
                        str(risk["estimated_value"]),
                        risk["reward_probability"],
                        f"{risk['risk_reward_ratio']:.2f}",
                        risk["date_created"],
                        risk["last_updated"]
                    ]
                    f.write(",".join(row) + "\n")
            
            QMessageBox.information(self, "Success", "Risks exported successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export risks: {str(e)}")

    def update_dashboard(self):
        # Update statistics
        total = len(self.risks)
        high_priority = sum(1 for risk in self.risks if risk["priority"] in ["Critical", "High"])
        medium_priority = sum(1 for risk in self.risks if risk["priority"] == "Medium")
        low_priority = sum(1 for risk in self.risks if risk["priority"] == "Low")
        
        self.total_risks_label.setText(f"Total Risks: {total}")
        self.high_risks_label.setText(f"High Priority: {high_priority}")
        self.medium_risks_label.setText(f"Medium Priority: {medium_priority}")
        self.low_risks_label.setText(f"Low Priority: {low_priority}")
        
        # Update recent activities
        self.update_recent_activities()

    def setup_shortcuts(self):
        # Add keyboard shortcuts
        self.shortcuts = {
            "Ctrl+N": (self.add_risk, "Add New Risk"),
            "Ctrl+S": (self.save_assessment, "Save Risk"),
            "Delete": (self.delete_risk, "Delete Risk"),
            "Ctrl+F": (lambda: self.risk_search.setFocus(), "Search"),
            "Ctrl+E": (self.export_to_csv, "Export to CSV")
        }
        
        for key, (func, _) in self.shortcuts.items():
            QShortcut(QKeySequence(key), self).activated.connect(func)

    def setup_status_bar(self):
        self.statusBar().showMessage("Ready")
        
        def update_status(message, timeout=3000):
            self.statusBar().showMessage(message, timeout)
        
        # Connect to various actions
        self.add_button.clicked.connect(
            lambda: update_status("New risk added")
        )
        self.save_button.clicked.connect(
            lambda: update_status("Risk saved successfully")
        )

    def calculate_risk_reward_ratio(self, risk: Dict) -> float:
        """Calculate the risk-reward ratio for a given risk.
        
        Args:
            risk: Dictionary containing risk information
            
        Returns:
            float: The calculated risk-reward ratio
        """
        # Risk level weights
        risk_weights = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        reward_weights = {"Low": 1, "Medium": 2, "High": 3}
        
        risk_score = (risk_weights[risk["probability"]] * 
                     risk_weights[risk["impact"]])
        
        reward_score = (reward_weights[risk["reward_probability"]] * 
                       (risk["estimated_value"] / 1000))  # Normalize value
        
        if risk_score == 0:
            return 0
        
        return reward_score / risk_score

    def update_analysis(self):
        try:
            current_row = self.risk_table.currentRow()
            if current_row >= 0:
                risk = self.risks[current_row]
                
                # Calculate risk-reward ratio
                ratio = self.calculate_risk_reward_ratio(risk)
                self.risk_reward_ratio.setText(f"Risk-Reward Ratio: {ratio:.2f}")
                
                # Calculate expected value
                prob_weights = {"Low": 0.3, "Medium": 0.5, "High": 0.7}
                expected = risk["estimated_value"] * prob_weights[risk["reward_probability"]]
                self.expected_value.setText(f"Expected Value: ${expected:,.2f}")
                
                # Generate recommendation
                if ratio > 2.0:
                    recommendation = "Highly Favorable - Proceed"
                    color = "green"
                elif ratio > 1.0:
                    recommendation = "Favorable - Proceed with caution"
                    color = "lightgreen"
                elif ratio > 0.5:
                    recommendation = "Marginal - Additional mitigation recommended"
                    color = "yellow"
                else:
                    recommendation = "Unfavorable - Reconsider or enhance rewards"
                    color = "red"
                
                self.recommendation.setText(f"Recommendation: {recommendation}")
                self.recommendation.setStyleSheet(f"color: {color}")
        except Exception as e:
            self.statusBar().showMessage(f"Error updating analysis: {str(e)}", 5000)
            self.risk_reward_ratio.setText("Risk-Reward Ratio: Error")
            self.expected_value.setText("Expected Value: Error")
            self.recommendation.setText("Recommendation: Error in calculation")

    def import_risk_registry(self):
        """Import risks from a JSON file (renamed from import_portfolio)"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Import Risk Registry",  # Updated dialog title
                "",
                "Risk Registry (*.json);;All Files (*)"  # Updated file type description
            )
            
            if file_name:
                with open(file_name, 'r') as f:
                    data = json.load(f)
                    
                    # Validate the imported data
                    if not isinstance(data, dict) or "risk_registry" not in data:  # Updated key name
                        raise ValueError("Invalid format: file must contain a 'risk_registry' object")
                    
                    required_fields = ["id", "description", "probability", "impact", 
                                     "priority", "status"]
                    
                    # Validate each risk
                    for risk in data["risk_registry"]:  # Updated key name
                        missing_fields = [field for field in required_fields 
                                        if field not in risk]
                        if missing_fields:
                            raise ValueError(
                                f"Risk {risk.get('id', 'unknown')} missing required "
                                f"fields: {', '.join(missing_fields)}"
                            )
                    
                    # Merge with existing risks
                    existing_ids = {risk["id"] for risk in self.risks}
                    new_risks = [risk for risk in data["risk_registry"]  # Updated key name
                                if risk["id"] not in existing_ids]
                    
                    # Add new risks
                    self.risks.extend(new_risks)
                    
                    # Add import history
                    for risk in new_risks:
                        self.add_to_history(
                            risk["id"], 
                            f"Imported from {os.path.basename(file_name)}"
                        )
                    
                    self.save_risks()
                    self.update_table()
                    self.update_dashboard()
                    
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Successfully imported {len(new_risks)} new risks"
                    )
        
        except json.JSONDecodeError:
            QMessageBox.warning(
                self,
                "Error",
                "Invalid JSON file format"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to import risks: {str(e)}"
            )

    def setup_client(self):
        # Load config from environment or file
        config = ApiConfig(
            base_url=os.getenv("RISKKIT_API_URL", "http://localhost:4000"),
            api_key=os.getenv("RISKKIT_API_KEY"),
            org_id=os.getenv("RISKKIT_ORG_ID")
        )
        
        self.client = RiskkitClient(config)
        
        # Setup event subscriptions
        self.client.subscribe("risks:created", lambda p: self.risk_created.emit(p))
        self.client.subscribe("risks:updated", lambda p: self.risk_updated.emit(p))
        self.client.subscribe("resources:updated", lambda p: self.resource_updated.emit(p))
        self.client.subscribe("news:created", lambda p: self.news_received.emit(p))

        # Connect to API
        asyncio.create_task(self.client.connect())

    # Signals for async events
    risk_created = pyqtSignal(dict)
    risk_updated = pyqtSignal(dict)
    resource_updated = pyqtSignal(dict)
    news_received = pyqtSignal(dict)

    def connect_signals(self):

        super().connect_signals()
        """Connect PyQt signals to handlers"""
        self.risk_created.connect(self.on_risk_created)
        self.risk_updated.connect(self.on_risk_updated)
        self.resource_updated.connect(self.on_resource_updated)
        self.news_received.connect(self.on_news_received)
        self.status_combo.currentTextChanged.connect(self.validate_status_transition)

        self.connection_status_changed.connect(self.update_connection_status)
        self.sync_status_changed.connect(self.update_sync_status)

    async def refresh_data(self):
        """Refresh all data from the API"""
        try:
            self.risks = await self.client.get_risks()
            self.resources = await self.client.get_resources()
            self.news = await self.client.get_news()
            self.update_ui()
        except Exception as e:
            self.show_error("Failed to refresh data", str(e))

    def show_error(self, title: str, message: str):
        """Show error dialog"""
        QMessageBox.warning(self, title, message)

    # ... rest of the UI code ...

    # Add new signals
    connection_status_changed = pyqtSignal(bool)
    sync_status_changed = pyqtSignal(str)

    def setup_status_indicators(self):
        """Setup status bar indicators"""
        self.connection_indicator = QLabel()
        self.sync_indicator = QLabel()
        self.statusBar().addPermanentWidget(self.connection_indicator)
        self.statusBar().addPermanentWidget(self.sync_indicator)
        
        # Update initial status
        self.update_connection_status(False)
        self.update_sync_status("Not synced")

    def update_connection_status(self, connected: bool):
        """Update connection status indicator"""
        self.connection_indicator.setText("🟢 Online" if connected else "🔴 Offline")
        self.connection_indicator.setStyleSheet(
            "color: green;" if connected else "color: red;"
        )

    def update_sync_status(self, status: str):
        """Update sync status indicator"""
        self.sync_indicator.setText(f"📡 {status}")

    
    async def add_risk(self):
        """Add risk with offline support"""
        try:
            risk_data = self.get_risk_form_data()
            response = await self.client.create_risk(risk_data)
            
            if response.get("status") == "queued":
                self.sync_status_changed.emit("Pending sync")
                self.statusBar().showMessage("Risk queued for sync")
            else:
                self.sync_status_changed.emit("Synced")
                self.statusBar().showMessage("Risk created successfully")
                
            self.update_ui()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create risk: {str(e)}")

    def toggle_offline_mode(self):
        """Toggle offline mode"""
        self.client.config.offline_mode = not self.client.config.offline_mode
        self.connection_status_changed.emit(not self.client.config.offline_mode)
        self.sync_status_changed.emit(
            "Offline mode" if self.client.config.offline_mode else "Online"
        )

    async def update_risk(self, risk_id: int, risk_data: Dict):
        try:
            response = await self.client.update_risk(risk_id, risk_data)
            
            if response.get("status") == "conflict":
                dialog = ConflictResolutionDialog(
                    response["data"]["_conflicts"],
                    self
                )
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # Get resolved data from dialog
                    resolved_data = dialog.get_resolved_data()
                    # Retry update with resolved data
                    response = await self.client.update_risk(risk_id, resolved_data)
            
            self.update_ui()
            self.statusBar().showMessage("Risk updated successfully")
            
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update risk: {str(e)}")

    def show_state_machine_editor(self):
        editor = StateMachineEditor(self.risk_state_machine, self)
        editor.exec()


    def validate_status_transition(self, new_status: str):
        """Validate status transition when combo box changes"""
        current_row = self.risk_table.currentRow()
        if current_row >= 0:
            risk = self.risks[current_row]
            risk_obj = Risk.from_dict(risk)
            
            # Basic context for validation
            context = {
                "owner": risk.get("owner", ""),
                "mitigation": self.mitigation_text.toPlainText(),
                "resources": risk.get("resources", [])
            }
            
            if not risk_obj.can_transition_to(new_status, context):
                self.status_combo.setCurrentText(risk["status"])
                QMessageBox.warning(
                    self,
                    "Invalid Transition",
                    f"Cannot transition from {risk['status']} to {new_status}\n"
                    "Make sure all required fields are filled."
                )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RiskManager()
    window.show()
    sys.exit(app.exec())
