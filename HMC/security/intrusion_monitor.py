from typing import Dict, Any, List, Set
import socket
import threading
import logging
import time
import json
from datetime import datetime
import psutil
from pathlib import Path
from collections import defaultdict
from datetime import timedelta


class IntrusionMonitor:
    def __init__(self, security_config: Any):
        self.security_config = security_config
        self.running = False
        self.monitored_ports: Set[int] = set()
        self.suspicious_ips: Dict[str, Dict[str, Any]] = {}
        self.patterns: Dict[str, List[str]] = {}
        self.monitor_threads: List[threading.Thread] = []
        self.lock = threading.Lock()
        self.log_path = Path("security_logs")
        self.log_path.mkdir(exist_ok=True)
        self.scan_attempts = defaultdict(list)  # Track scan patterns
        self.scan_thresholds = {
            "ports_per_minute": 5,
            "syn_scan_threshold": 3,
            "null_scan_threshold": 2,
            "fin_scan_threshold": 2
        }
        self.last_scan_alert = None
        self.scan_alert_cooldown = timedelta(minutes=5)
        
        # HTTP/HTTPS monitoring
        self.http_patterns = {
            "sql_injection": [
                "UNION SELECT", 
                "OR 1=1", 
                "DROP TABLE",
                "--"
            ],
            "xss": [
                "<script>",
                "javascript:",
                "onerror=",
                "onload="
            ],
            "path_traversal": [
                "../",
                "..\\",
                "/etc/passwd",
                "c:\\windows"
            ],
            "command_injection": [
                ";",
                "|",
                "$(", 
                "`"
            ]
        }
        
        # WebSocket monitoring
        self.ws_connections = {}
        self.ws_patterns = {
            "flood": 50,  # messages per second
            "large_payload": 1000000,  # bytes
            "suspicious_commands": [
                "eval(",
                "exec(",
                "system("
            ]
        }
        
        # Email/Link monitoring
        self.suspicious_domains = set()
        self.link_patterns = {
            "phishing": [
                r"bank.*\.com",
                r"account.*verify",
                r"login.*secure"
            ],
            "malware": [
                r"\.exe$",
                r"\.zip$",
                r"\.scr$"
            ]
        }
        
    def start(self):
        """Start monitoring"""
        self.running = True
        self._start_log_rotation()
        
    def stop(self):
        """Stop all monitoring"""
        self.running = False
        for thread in self.monitor_threads:
            thread.join(timeout=1.0)
            
    def is_running(self) -> bool:
        return self.running
        
    def monitor_port(self, port: int):
        """Start monitoring a specific port"""
        if port in self.monitored_ports:
            return
            
        self.monitored_ports.add(port)
        thread = threading.Thread(
            target=self._port_monitor_worker,
            args=(port,),
            daemon=True
        )
        self.monitor_threads.append(thread)
        thread.start()
        
    def set_patterns(self, patterns: Dict[str, List[str]]):
        """Set patterns to monitor for"""
        self.patterns = patterns

    def detect_scan(self, ip: str, port: int, packet_type: str = "SYN"):
        """Detect potential port scanning"""
        current_time = datetime.now()
        
        # Add scan attempt
        self.scan_attempts[ip].append({
            "time": current_time,
            "port": port,
            "type": packet_type
        })
        
        # Clean old attempts
        self.scan_attempts[ip] = [
            attempt for attempt in self.scan_attempts[ip]
            if current_time - attempt["time"] < timedelta(minutes=1)
        ]
        
        # Analyze scan pattern
        scan_info = self._analyze_scan_pattern(ip)
        
        if scan_info["is_scanning"]:
            self._handle_scan_detection(ip, scan_info)
        
    def _port_monitor_worker(self, port: int):
        """Worker thread for monitoring a port"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', port))
        sock.listen(1)
        sock.settimeout(1.0)
        
        while self.running:
            try:
                conn, addr = sock.accept()
                self._handle_connection(conn, addr, port)
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Port monitor error on {port}: {e}")
                
        sock.close()
        
    def _handle_connection(self, conn: socket.socket, addr: tuple, port: int):
        """Handle incoming connection"""
        try:
            ip = addr[0]
            
            # Check if IP is already blacklisted
            if self._is_blacklisted(ip):
                conn.close()
                return
                
            # Record connection attempt
            self._record_attempt(ip, port)
            
            # Check for suspicious behavior
            if self._is_suspicious(ip):
                self._handle_suspicious(ip, port)
                
            # Apply deception if enabled
            if self.security_config.monitoring["deception"]["enabled"]:
                self._apply_deception(conn, ip)
                
            # Log connection
            self._log_connection(ip, port)
            
        except Exception as e:
            logging.error(f"Connection handler error: {e}")
        finally:
            conn.close()
            
    def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        return ip in self.security_config.authentication["policies"]["ip_blacklist"]
        
    def _record_attempt(self, ip: str, port: int):
        """Record connection attempt"""
        with self.lock:
            if ip not in self.suspicious_ips:
                self.suspicious_ips[ip] = {
                    "attempts": 0,
                    "first_seen": datetime.now(),
                    "ports": set(),
                    "patterns": []
                }
            
            self.suspicious_ips[ip]["attempts"] += 1
            self.suspicious_ips[ip]["ports"].add(port)
            
    def _is_suspicious(self, ip: str) -> bool:
        """Check if IP shows suspicious behavior"""
        if ip not in self.suspicious_ips:
            return False
            
        data = self.suspicious_ips[ip]
        
        # Check number of attempts
        if data["attempts"] >= self.security_config.countermeasures["alerts"]["thresholds"]["attempts"]:
            return True
            
        # Check port scanning
        if len(data["ports"]) > 3:  # More than 3 different ports
            return True
            
        # Check known patterns
        if data["patterns"]:
            return True
            
        return False
        
    def _handle_suspicious(self, ip: str, port: int):
        """Handle suspicious IP"""
        try:
            # Log suspicious activity
            self._log_suspicious(ip, port)
            
            # Apply countermeasures
            response = self.security_config.countermeasures["active_defense"]["responses"]
            
            if "port_scan" in response and len(self.suspicious_ips[ip]["ports"]) > 3:
                self._add_to_blacklist(ip)
                
            if "brute_force" in response and self.suspicious_ips[ip]["attempts"] > 10:
                self._trigger_challenge(ip)
                
        except Exception as e:
            logging.error(f"Error handling suspicious IP {ip}: {e}")
            
    def _apply_deception(self, conn: socket.socket, ip: str):
        """Apply deception techniques"""
        try:
            if self.security_config.monitoring["deception"]["delayed_responses"]["enabled"]:
                time.sleep(self.security_config.monitoring["deception"]["delayed_responses"]["delay_ms"] / 1000)
                
            fake_error = self.security_config.monitoring["deception"]["fake_errors"]["templates"]["403"]
            conn.send(fake_error.encode())
            
        except Exception as e:
            logging.error(f"Error applying deception: {e}")
            
    def _log_connection(self, ip: str, port: int):
        """Log connection details"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "ip": ip,
                "port": port,
                "suspicious": self._is_suspicious(ip),
                "attempts": self.suspicious_ips[ip]["attempts"]
            }
            
            log_file = self.log_path / f"connections_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, 'a') as f:
                json.dump(log_entry, f)
                f.write('\n')
                
        except Exception as e:
            logging.error(f"Error logging connection: {e}")
            
    def _log_suspicious(self, ip: str, port: int):
        """Log suspicious activity"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "ip": ip,
                "port": port,
                "activity": {
                    "attempts": self.suspicious_ips[ip]["attempts"],
                    "ports": list(self.suspicious_ips[ip]["ports"]),
                    "patterns": self.suspicious_ips[ip]["patterns"]
                }
            }
            
            log_file = self.log_path / "suspicious_activity.log"
            with open(log_file, 'a') as f:
                json.dump(log_entry, f)
                f.write('\n')
                
        except Exception as e:
            logging.error(f"Error logging suspicious activity: {e}")
            
    def _start_log_rotation(self):
        """Start log rotation thread"""
        def rotate_logs():
            while self.running:
                try:
                    # Delete logs older than 30 days
                    current_time = datetime.now()
                    for log_file in self.log_path.glob("*.log"):
                        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if (current_time - file_time).days > 30:
                            log_file.unlink()
                except Exception as e:
                    logging.error(f"Log rotation error: {e}")
                time.sleep(86400)  # Check daily
                
        threading.Thread(target=rotate_logs, daemon=True).start()

    def _analyze_scan_pattern(self, ip: str) -> dict:
        """Analyze scanning pattern for an IP"""
        attempts = self.scan_attempts[ip]
        unique_ports = len(set(a["port"] for a in attempts))
        
        pattern = {
            "is_scanning": False,
            "scan_type": None,
            "ports_hit": unique_ports,
            "techniques": [],
            "intensity": "low"
        }
        
        # Check scan speed
        if unique_ports >= self.scan_thresholds["ports_per_minute"]:
            pattern["is_scanning"] = True
            pattern["techniques"].append("port_sweep")
            
        # Check for SYN scans (half-open scanning)
        syn_attempts = sum(1 for a in attempts if a["type"] == "SYN")
        if syn_attempts >= self.scan_thresholds["syn_scan_threshold"]:
            pattern["is_scanning"] = True
            pattern["techniques"].append("syn_scan")
            
        # Check for stealth scanning
        null_attempts = sum(1 for a in attempts if a["type"] == "NULL")
        fin_attempts = sum(1 for a in attempts if a["type"] == "FIN")
        
        if null_attempts >= self.scan_thresholds["null_scan_threshold"]:
            pattern["is_scanning"] = True
            pattern["techniques"].append("null_scan")
            
        if fin_attempts >= self.scan_thresholds["fin_scan_threshold"]:
            pattern["is_scanning"] = True
            pattern["techniques"].append("fin_scan")
            
        # Determine intensity
        if unique_ports > 20:
            pattern["intensity"] = "high"
        elif unique_ports > 10:
            pattern["intensity"] = "medium"
            
        return pattern
        
    def _handle_scan_detection(self, ip: str, scan_info: dict):
        """Handle detected port scan"""
        current_time = datetime.now()
        
        # Check cooldown
        if (self.last_scan_alert and 
            current_time - self.last_scan_alert < self.scan_alert_cooldown):
            return
            
        self.last_scan_alert = current_time
        
        # Log the scan
        log_entry = {
            "timestamp": current_time.isoformat(),
            "ip": ip,
            "scan_type": scan_info["techniques"],
            "intensity": scan_info["intensity"],
            "ports_scanned": scan_info["ports_hit"]
        }
        
        # Try to fingerprint the scanner
        scanner_info = self._fingerprint_scanner(ip)
        if scanner_info:
            log_entry["scanner_info"] = scanner_info
            
        # Log to special scan detection file
        scan_log = self.log_path / "scan_detection.log"
        with open(scan_log, 'a') as f:
            json.dump(log_entry, f)
            f.write('\n')
            
        # Alert if configured
        if self.security_config.monitoring["alerts"]["enabled"]:
            self._send_scan_alert(log_entry)
            
    def _fingerprint_scanner(self, ip: str) -> dict:
        """Try to fingerprint the scanning tool"""
        try:
            nm = nmap.PortScanner()
            result = nm.scan(ip, arguments="-O -sV")
            
            if ip in result["scan"]:
                host_info = result["scan"][ip]
                return {
                    "os": host_info.get("osmatch", [{}])[0].get("name", "unknown"),
                    "accuracy": host_info.get("osmatch", [{}])[0].get("accuracy", "0"),
                    "services": host_info.get("tcp", {})
                }
        except Exception as e:
            logging.error(f"Error fingerprinting scanner: {e}")
        return None
        
    def _send_scan_alert(self, scan_info: dict):
        """Send alert about detected scan"""
        alert = f"""Port Scan Detected!
IP: {scan_info['ip']}
Time: {scan_info['timestamp']}
Type: {', '.join(scan_info['scan_type'])}
Intensity: {scan_info['intensity']}
Ports Scanned: {scan_info['ports_scanned']}
"""
        if "scanner_info" in scan_info:
            alert += f"\nScanner OS: {scan_info['scanner_info']['os']}"
            
        # Log alert
        logging.warning(alert)
        
        # Send to configured channels
        for channel in self.security_config.countermeasures["alerts"]["channels"]:
            self._send_alert_to_channel(channel, alert)