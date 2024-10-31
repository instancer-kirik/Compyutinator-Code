from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtNetwork import QAbstractSocket
import json
import logging
from typing import Optional, Dict, Any
from enum import Enum

class WebSocketState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class WebSocketClient(QObject):
    # Signals for connection state
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    state_changed = pyqtSignal(WebSocketState)

    # Signals for different resource types
    risk_created = pyqtSignal(dict)
    risk_updated = pyqtSignal(dict)
    risk_deleted = pyqtSignal(int)  # risk_id

    mitigation_created = pyqtSignal(dict)
    mitigation_updated = pyqtSignal(dict)
    mitigation_deleted = pyqtSignal(int)

    task_created = pyqtSignal(dict)
    task_updated = pyqtSignal(dict)
    task_completed = pyqtSignal(dict)

    # Add new signals for news and events
    news_received = pyqtSignal(dict)
    event_received = pyqtSignal(dict)
    notification_received = pyqtSignal(dict)
    system_status_updated = pyqtSignal(dict)

    def __init__(self, base_url: str, token: str, event_manager: EventManager = None):
        super().__init__()
        self.base_url = base_url
        self.token = token
        self.event_manager = event_manager
        
        # Initialize WebSocket
        self.socket = QWebSocket()
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.textMessageReceived.connect(self._on_message)
        self.socket.error.connect(self._on_error)
        
        # Connection state
        self.current_state = WebSocketState.DISCONNECTED
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Setup reconnection timer
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setInterval(5000)  # 5 seconds
        self.reconnect_timer.timeout.connect(self._try_reconnect)
        
        # Track subscriptions
        self.subscribed_channels = {
            "projects": set(),
            "news": False,
            "events": False,
            "system": False
        }
        
        # Operation tracking
        self.operation_counter = 0

    def connect_to_server(self):
        """Initiate connection to WebSocket server"""
        if self.current_state != WebSocketState.CONNECTED:
            self._set_state(WebSocketState.CONNECTING)
            url = f"{self.base_url}/socket/websocket?token={self.token}"
            self.socket.open(url)

    def disconnect(self):
        """Cleanly disconnect from server"""
        self.reconnect_timer.stop()
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.close()

    def subscribe_to_project(self, project_id: int):
        """Enhanced project subscription with operation tracking"""
        if self.current_state == WebSocketState.CONNECTED:
            op_id = self._get_operation_id()
            if self.event_manager:
                self.event_manager.register_operation(op_id)
            
            message = {
                "topic": f"project:{project_id}",
                "event": "phx_join",
                "payload": {},
                "ref": op_id
            }
            self.socket.sendTextMessage(json.dumps(message))
            self.subscribed_channels["projects"].add(str(project_id))
            
            # Cleanup operation after timeout
            QTimer.singleShot(5000, lambda: self._cleanup_operation(op_id))

    def subscribe_to_channel(self, channel: str, **kwargs):
        """Subscribe to a specific channel type"""
        if self.current_state == WebSocketState.CONNECTED:
            message = {
                "topic": f"{channel}",
                "event": "phx_join",
                "payload": kwargs,
                "ref": channel
            }
            self.socket.sendTextMessage(json.dumps(message))
            
            if channel == "news":
                self.subscribed_channels["news"] = True
            elif channel == "events":
                self.subscribed_channels["events"] = True
            elif channel == "system":
                self.subscribed_channels["system"] = True
            logging.info(f"Subscribed to channel: {channel}")

    def subscribe_to_all_channels(self):
        """Subscribe to all available channels"""
        self.subscribe_to_channel("news")
        self.subscribe_to_channel("events")
        self.subscribe_to_channel("system")
        logging.info("Subscribed to all channels")

    def unsubscribe_from_project(self, project_id: int):
        """Unsubscribe from a project's updates"""
        if self.current_state == WebSocketState.CONNECTED:
            message = {
                "topic": f"project:{project_id}",
                "event": "phx_leave",
                "payload": {},
                "ref": str(project_id)
            }
            self.socket.sendTextMessage(json.dumps(message))
            self.subscribed_channels["projects"].discard(str(project_id))

    def _set_state(self, new_state: WebSocketState):
        """Update connection state and emit signal"""
        if new_state != self.current_state:
            self.current_state = new_state
            self.state_changed.emit(new_state)

    def _on_connected(self):
        """Handle successful connection"""
        self._set_state(WebSocketState.CONNECTED)
        self.connected.emit()
        self.reconnect_attempts = 0
        self.reconnect_timer.stop()

        # Resubscribe to previous channels
        for project_id in self.subscribed_channels["projects"]:
            self.subscribe_to_project(int(project_id))
        
        # Resubscribe to all channels
        if self.subscribed_channels["news"]:
            self.subscribe_to_channel("news")
        if self.subscribed_channels["events"]:
            self.subscribe_to_channel("events")
        if self.subscribed_channels["system"]:
            self.subscribe_to_channel("system")

    def _on_disconnected(self):
        """Handle disconnection"""
        self._set_state(WebSocketState.DISCONNECTED)
        self.disconnected.emit()
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_timer.start()

    def _on_error(self, error_code):
        """Enhanced error handling with event manager"""
        error_msg = f"WebSocket error: {error_code} - {self.socket.errorString()}"
        self._set_state(WebSocketState.ERROR)
        self.error.emit(error_msg)
        
        if self.event_manager:
            self.event_manager.broadcast_news(
                "WebSocket Error",
                error_msg,
                EventPriority.HIGH
            )
        
        logging.error(error_msg)

    def _try_reconnect(self):
        """Attempt to reconnect to server"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logging.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            self.connect_to_server()
        else:
            self.reconnect_timer.stop()
            self.error.emit("Max reconnection attempts reached")

    def _on_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            topic = data.get("topic", "")
            event = data.get("event")
            payload = data.get("payload", {})

            if event == "phx_reply" and payload.get("status") == "ok":
                # Handle successful channel join
                return

            # Handle different channel types
            if topic.startswith("project:"):
                self._handle_project_message(event, payload)
            elif topic == "news":
                self._handle_news_message(event, payload)
            elif topic == "events":
                self._handle_event_message(event, payload)
            elif topic == "system":
                self._handle_system_message(event, payload)

        except json.JSONDecodeError:
            logging.error(f"Invalid JSON message received: {message}")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")

    def _handle_project_message(self, event: str, payload: dict):
        """Handle project-specific messages"""
        if event == "risk:created":
            self.risk_created.emit(payload)
        elif event == "risk:updated":
            self.risk_updated.emit(payload)
        elif event == "risk:deleted":
            self.risk_deleted.emit(payload.get("id"))
        elif event == "mitigation:created":
            self.mitigation_created.emit(payload)
        elif event == "mitigation:updated":
            self.mitigation_updated.emit(payload)
        elif event == "task:completed":
            self.task_completed.emit(payload)

    def _handle_news_message(self, event: str, payload: dict):
        """Enhanced news handler with event manager integration"""
        if event == "news:broadcast" and self.event_manager:
            priority = EventPriority[payload.get("priority", "NORMAL").upper()]
            self.event_manager.broadcast_news(
                payload.get("title", ""),
                payload.get("message", ""),
                priority
            )
        
        self.news_received.emit(payload)

    def _handle_event_message(self, event: str, payload: dict):
        """Handle event channel messages"""
        if event == "event:new":
            self.event_received.emit(payload)

    def _handle_system_message(self, event: str, payload: dict):
        """Enhanced system message handler with event manager integration"""
        if not self.event_manager:
            return

        if event == "system:maintenance_start":
            self.event_manager.system_event.emit(
                SystemEvent.MAINTENANCE_STARTED,
                payload
            )
        elif event == "system:maintenance_end":
            self.event_manager.system_event.emit(
                SystemEvent.MAINTENANCE_ENDED,
                payload
            )
        elif event == "system:update_available":
            self.event_manager.system_event.emit(
                SystemEvent.UPDATE_AVAILABLE,
                payload
            )
        elif event == "system:disk_space_warning":
            self.event_manager.system_event.emit(
                SystemEvent.DISK_SPACE_LOW,
                payload
            )
        
        self.system_status_updated.emit(payload)

    def _get_operation_id(self) -> str:
        """Generate unique operation ID"""
        self.operation_counter += 1
        return f"ws_op_{self.operation_counter}"

    def _cleanup_operation(self, op_id: str):
        """Cleanup registered operations"""
        if self.event_manager:
            self.event_manager.unregister_operation(op_id)