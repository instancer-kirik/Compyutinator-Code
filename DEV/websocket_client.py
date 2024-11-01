from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtNetwork import QAbstractSocket
import json
import logging
from typing import Optional, Dict, Any
from enum import Enum
from riskkit.client import RiskkitClient
from riskkit.enums import EventPriority
from riskkit.events import EventManager, SystemEvent

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
    auth_failed = pyqtSignal(str)

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
    user_presence_changed = pyqtSignal(int, bool)  # user_id, is_online

    def __init__(self, base_url: str, token: str, event_manager: EventManager = None):
        super().__init__()
        # Enforce WSS for non-localhost
        if not base_url.startswith(('wss://', 'ws://')):
            base_url = f"wss://{base_url}"
        elif base_url.startswith('ws://') and not base_url.startswith('ws://localhost'):
            base_url = f"wss://{base_url[5:]}"
            
        self.base_url = base_url
        self.token = token
        self.event_manager = event_manager
        
        # Initialize WebSocket with security headers
        self.socket = QWebSocket()
        self.socket.setProperty("Authorization", f"Bearer {self.token}")
        self.socket.setProperty("X-Client-Version", "1.0.0")
        
        # Add message validation tracking
        self.last_message_time = 0
        self.message_count = 0
        self.rate_limit_window = 60  # 60 seconds
        self.rate_limit_max = 100    # max 100 messages per minute
        
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
        self.ref_counter = 0
        self.channels = {}

        # Connect socket signals
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.textMessageReceived.connect(self._on_message)
        self.socket.error.connect(self._on_error)

    def connect_to_server(self):
        """Connect to Phoenix WebSocket server with security checks"""
        if self.current_state != WebSocketState.CONNECTED:
            self._set_state(WebSocketState.CONNECTING)
            
            # Add security parameters
            params = {
                "token": self.token,
                "vsn": "2.0.0",
                "client_version": "1.0.0"
            }
            param_string = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{self.base_url}/socket/websocket?{param_string}"
            
            self.socket.open(url)

    def disconnect(self):
        """Cleanly disconnect from server"""
        self.reconnect_timer.stop()
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.close()

    def subscribe_to_project(self, project_id: int):
        """Subscribe to project-specific channels"""
        self.join_channel(f"risks:{project_id}")
        self.join_channel(f"project:{project_id}")

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

    def _validate_message(self, data: dict) -> bool:
        """Validate incoming messages for rate limiting and structure"""
        current_time = time.time()
        
        # Rate limiting
        if current_time - self.last_message_time > self.rate_limit_window:
            self.message_count = 0
            self.last_message_time = current_time
        
        self.message_count += 1
        if self.message_count > self.rate_limit_max:
            logging.warning("Rate limit exceeded")
            return False

        # Message structure validation
        required_fields = ["topic", "event", "payload"]
        if not all(field in data for field in required_fields):
            logging.warning("Invalid message structure")
            return False

        # Payload size validation (prevent memory attacks)
        payload_size = len(json.dumps(data.get("payload", {})))
        if payload_size > 1024 * 1024:  # 1MB limit
            logging.warning("Message payload too large")
            return False

        return True

    def _on_message(self, message: str):
        """Handle Phoenix channel messages with security validation"""
        try:
            data = json.loads(message)
            
            # Validate message before processing
            if not self._validate_message(data):
                logging.warning("Message validation failed")
                return
                
            # Handle authentication errors
            if data.get("event") == "phx_error":
                if "unauthorized" in str(data.get("payload")):
                    self.auth_failed.emit("Authentication failed")
                    return

            topic = data.get("topic", "")
            event = data.get("event")
            payload = data.get("payload", {})

            # Add security audit logging for sensitive operations
            if event in ["user:join", "user:leave", "system:update"]:
                logging.info(f"Security audit: {event} from {topic}")

            # Handle join responses
            if event == "phx_reply":
                if payload.get("status") == "ok":
                    logging.info(f"Successfully joined channel: {topic}")
                return

            # Handle different types of messages
            if topic.startswith("risks:"):
                self._handle_risk_event(event, payload)
            elif topic.startswith("project:"):
                self._handle_project_event(event, payload)
            elif topic.startswith("user:"):
                self._handle_user_message(event, payload)
            elif topic == "system":
                self._handle_system_event(event, payload)

        except json.JSONDecodeError:
            logging.error(f"Invalid JSON message received")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")

    def _handle_risk_event(self, event: str, payload: dict):
        """Handle risk-related events"""
        if event == "risk:created":
            self.risk_created.emit(payload)
        elif event == "risk:updated":
            self.risk_updated.emit(payload)
        elif event == "risk:deleted":
            self.risk_deleted.emit(payload.get("id"))

    def _handle_project_event(self, event: str, payload: dict):
        """Handle project-specific events"""
        if event == "mitigation:created":
            self.mitigation_created.emit(payload)
        elif event == "mitigation:updated":
            self.mitigation_updated.emit(payload)
        elif event == "task:completed":
            self.task_completed.emit(payload)

    def _handle_system_event(self, event: str, payload: dict):
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

    def _handle_user_message(self, event: str, payload: dict):
        """Handle user-related messages with security checks"""
        # Validate user IDs
        if "from_user_id" in payload and not isinstance(payload["from_user_id"], int):
            logging.warning("Invalid user ID in message")
            return
            
        if event == "presence_diff":
            for user_id in payload.get("joins", {}):
                self.user_presence_changed.emit(int(user_id), True)
            for user_id in payload.get("leaves", {}):
                self.user_presence_changed.emit(int(user_id), False)

    @staticmethod
    def _sanitize_content(content: str) -> str:
        """Basic content sanitization"""
        # Add basic sanitization - extend as needed
        import html
        content = html.escape(content)
        return content

    def _get_operation_id(self) -> str:
        """Generate unique operation ID"""
        self.operation_counter += 1
        return f"ws_op_{self.operation_counter}"

    def _cleanup_operation(self, op_id: str):
        """Cleanup registered operations"""
        if self.event_manager:
            self.event_manager.unregister_operation(op_id)

    def _get_ref(self) -> str:
        """Get unique Phoenix message reference"""
        self.ref_counter += 1
        return str(self.ref_counter)

    def join_channel(self, topic: str, params: dict = None):
        """Join a Phoenix channel"""
        if self.current_state == WebSocketState.CONNECTED:
            ref = self._get_ref()
            message = {
                "topic": topic,
                "event": "phx_join",
                "payload": params or {},
                "ref": ref
            }
            self.socket.sendTextMessage(json.dumps(message))
            self.channels[topic] = ref
            logging.info(f"Joining channel: {topic}")

    def leave_channel(self, topic: str):
        """Leave a Phoenix channel"""
        if topic in self.channels:
            message = {
                "topic": topic,
                "event": "phx_leave",
                "payload": {},
                "ref": self._get_ref()
            }
            self.socket.sendTextMessage(json.dumps(message))
            del self.channels[topic]
            logging.info(f"Left channel: {topic}")