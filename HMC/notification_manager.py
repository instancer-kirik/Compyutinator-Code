from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea, QFrame, QSizePolicy
)
from datetime import datetime, timedelta
import uuid
from typing import Dict, List
from riskkit.events import Notification, NotificationType, NotificationPriority
from typing import Optional

class NotificationWidget(QFrame):
    dismissed = pyqtSignal(str)  # notification_id
    action_triggered = pyqtSignal(str, str)  # notification_id, action

    def __init__(self, notification: Notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        type_label = QLabel(f"[{self.notification.type.value}]")
        type_label.setStyleSheet(self._get_type_style())
        header_layout.addWidget(type_label)
        
        title_label = QLabel(self.notification.title)
        title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        timestamp = QLabel(self.notification.timestamp.strftime("%H:%M"))
        timestamp.setStyleSheet("color: gray;")
        header_layout.addWidget(timestamp)
        
        layout.addLayout(header_layout)
        
        # Message
        message_label = QLabel(self.notification.message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Action button if available
        if self.notification.action:
            action_btn = QPushButton(self.notification.action)
            action_btn.clicked.connect(
                lambda: self.action_triggered.emit(
                    self.notification.id, 
                    self.notification.action
                )
            )
            layout.addWidget(action_btn)

        # Dismiss button
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.clicked.connect(
            lambda: self.dismissed.emit(self.notification.id)
        )
        layout.addWidget(dismiss_btn)

    def _get_type_style(self) -> str:
        colors = {
            NotificationType.SYSTEM: "#007AFF",
            NotificationType.SECURITY: "#FF3B30",
            NotificationType.UPDATE: "#5856D6",
            NotificationType.NETWORK: "#FF9500",
            NotificationType.DATA: "#4CD964",
            NotificationType.USER: "#5AC8FA",
            NotificationType.NEWS: "#FFCC00"
        }
        return f"color: {colors.get(self.notification.type, '#000000')};"

class NotificationCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications: Dict[str, NotificationWidget] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Notifications")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.notification_container = QWidget()
        self.notification_layout = QVBoxLayout(self.notification_container)
        self.notification_layout.addStretch()
        
        scroll.setWidget(self.notification_container)
        layout.addWidget(scroll)

    def add_notification(self, notification: Notification):
        widget = NotificationWidget(notification)
        widget.dismissed.connect(self.remove_notification)
        widget.action_triggered.connect(self.handle_action)
        
        self.notifications[notification.id] = widget
        self.notification_layout.insertWidget(0, widget)

    def remove_notification(self, notification_id: str):
        if notification_id in self.notifications:
            widget = self.notifications.pop(notification_id)
            self.notification_layout.removeWidget(widget)
            widget.deleteLater()

    def clear_all(self):
        for widget in self.notifications.values():
            widget.deleteLater()
        self.notifications.clear()
    def handle_action(self, notification_id: str, action: str):
        # Handle notification actions here
        print(f"Action {action} triggered for notification {notification_id}")

class NotificationManager(QObject):
    notification_added = pyqtSignal(Notification)
    notification_removed = pyqtSignal(str)  # notification_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications: Dict[str, Notification] = {}
        
        # Create timer with parent to ensure it runs in Qt event loop
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.cleanup_expired)
        # Start timer after moving to thread
        QTimer.singleShot(0, lambda: self.cleanup_timer.start(60000))

    def add_notification(
        self,
        type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        action: Optional[str] = None,
        data: Optional[dict] = None,
        expires_in: Optional[timedelta] = None
    ) -> str:
        notification_id = str(uuid.uuid4())
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + expires_in

        notification = Notification(
            id=notification_id,
            type=type,
            priority=priority,
            title=title,
            message=message,
            timestamp=datetime.now(),
            action=action,
            data=data,
            expires_at=expires_at
        )

        self.notifications[notification_id] = notification
        self.notification_added.emit(notification)
        return notification_id

    def remove_notification(self, notification_id: str):
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            self.notification_removed.emit(notification_id)

    def cleanup_expired(self):
        now = datetime.now()
        expired = [
            nid for nid, notif in self.notifications.items()
            if notif.expires_at and notif.expires_at <= now
        ]
        for nid in expired:
            self.remove_notification(nid)

    def get_active_notifications(self) -> List[Notification]:
        return list(self.notifications.values())
