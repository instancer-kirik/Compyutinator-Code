from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import logging
import json
from pathlib import Path
from datetime import datetime
import socket
import subprocess
import psutil
import threading
import hashlib
import os
import random
import time
from HMC.project_config import SecurityConfig
from HMC.security.intrusion_monitor import IntrusionMonitor

class SecurityConfigurator:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.security_config = SecurityConfig()
        self.load_config()
        self.intrusion_monitor = IntrusionMonitor(self.security_config)
        self.control_port = None
        self.control_token = None
        self._setup_remote_control()
        
    def load_config(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    self.security_config = SecurityConfig(**config_data)
        except Exception as e:
            logging.error(f"Error loading security config: {e}")
            
    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.security_config.to_dict(), f, indent=2)
        except Exception as e:
            logging.error(f"Error saving security config: {e}")

    def setup_honeypots(self):
        """Configure honeypot traps"""
        
        try:
            # Setup fake services
            for service, config in self.security_config.countermeasures["deception"]["fake_services"].items():
                port = config.get("port")
                if port:
                    self._create_honeypot_service(port)
                    
            # Setup decoy endpoints
            for endpoint in self.security_config.authentication["honeypot"]["fake_endpoints"]:
                self._create_decoy_endpoint(endpoint)
                
        except Exception as e:
            logging.error(f"Error setting up honeypots: {e}")

    def _create_honeypot_service(self, port: int):
        """Create a fake service listener"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('0.0.0.0', port))
            sock.listen(1)
            # Start monitoring thread for this honeypot
            self.intrusion_monitor.monitor_port(port)
        except Exception as e:
            logging.error(f"Error creating honeypot service on port {port}: {e}")

    def setup_countermeasures(self):
        """Configure active defense measures"""
        if self.security_config.countermeasures["active_defense"]["enabled"]:
            self._setup_port_monitoring()
            self._setup_traffic_analysis()
            self._create_tarpits()

    def _setup_port_monitoring(self):
        """Monitor for port scans"""
        try:
            # Get list of all listening ports
            connections = psutil.net_connections()
            listening_ports = [conn.laddr.port for conn in connections if conn.status == 'LISTEN']
            
            # Monitor these ports
            for port in listening_ports:
                self.intrusion_monitor.monitor_port(port)
        except Exception as e:
            logging.error(f"Error setting up port monitoring: {e}")

    def _setup_traffic_analysis(self):
        """Setup network traffic analysis"""
        try:
            if self.security_config.monitoring["intrusion_detection"]["enabled"]:
                patterns = self.security_config.monitoring["intrusion_detection"]["patterns"]
                self.intrusion_monitor.set_patterns(patterns)
        except Exception as e:
            logging.error(f"Error setting up traffic analysis: {e}")

    def _create_tarpits(self):
        """Create tarpit traps"""
        try:
            for tarpit in self.security_config.countermeasures["active_defense"]["traps"]["tarpits"]:
                self._setup_tarpit(tarpit)
        except Exception as e:
            logging.error(f"Error creating tarpits: {e}")

    def _setup_remote_control(self):
        """Setup secure remote control channel"""
        try:
            self.control_token = hashlib.sha256(os.urandom(32)).hexdigest()
            self.control_port = self._get_safe_port()
            threading.Thread(target=self._run_control_server, daemon=True).start()
            self._save_control_info()
        except Exception as e:
            logging.error(f"Error setting up remote control: {e}")

    def _run_control_server(self):
        """Run the remote control server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('0.0.0.0', self.control_port))
            sock.listen(1)
            
            while True:
                conn, addr = sock.accept()
                threading.Thread(target=self._handle_control_connection, 
                              args=(conn, addr)).start()
        except Exception as e:
            logging.error(f"Control server error: {e}")

    def _handle_control_connection(self, conn: socket.socket, addr: tuple):
        """Handle incoming control connection"""
        try:
            data = conn.recv(1024).decode()
            if not self._verify_control_token(data):
                conn.send(b"Invalid token")
                conn.close()
                return
                
            while True:
                cmd = conn.recv(1024).decode()
                if not cmd:
                    break
                response = self._handle_control_command(cmd, addr)
                conn.send(response.encode())
        except Exception as e:
            logging.error(f"Error handling control connection: {e}")
        finally:
            conn.close()

    def _handle_control_command(self, cmd: str, addr: tuple) -> str:
        """Handle control commands"""
        try:
            parts = cmd.split()
            if not parts:
                return "Invalid command"
                
            command = parts[0].lower()
            if command == "shutdown":
                if len(parts) < 2:
                    return "Missing target"
                target = parts[1]
                if self._verify_target(target, addr):
                    self._initiate_shutdown()
                    return "Shutdown initiated"
                return "Invalid target"
            elif command == "status":
                return self._get_status()
            return "Unknown command"
        except Exception as e:
            logging.error(f"Error handling command: {e}")
            return f"Error: {e}"

    def _cleanup(self):
        """Cleanup before shutdown"""
        try:
            self.intrusion_monitor.stop()
            if os.path.exists(self._get_control_path()):
                os.remove(self._get_control_path())
            if hasattr(self, 'sock'):
                self.sock.close()
        except Exception as e:
            logging.error(f"Cleanup error: {e}")

    def _verify_control_token(self, token: str) -> bool:
        return token == self.control_token

    def _verify_target(self, target: str, addr: tuple) -> bool:
        try:
            target_ip = socket.gethostbyname(target)
            return target_ip == addr[0]
        except:
            return False

    def _get_safe_port(self) -> int:
        while True:
            port = random.randint(49152, 65535)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', port))
                s.close()
                return port
            except:
                continue

    def _save_control_info(self):
        try:
            control_info = {
                "port": self.control_port,
                "token": self.control_token
            }
            with open(self._get_control_path(), 'w') as f:
                json.dump(control_info, f)
            os.chmod(self._get_control_path(), 0o600)
        except Exception as e:
            logging.error(f"Error saving control info: {e}")

    def _get_control_path(self) -> str:
        return str(self.config_path.parent / ".control")

    def _get_status(self) -> str:
        """Get current security status"""
        return json.dumps({
            "honeypots": len(self.security_config.countermeasures["deception"]["fake_services"]),
            "monitoring": self.intrusion_monitor.is_running(),
            "port": self.control_port
        })