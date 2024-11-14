
class DeviceCommand:
    def __init__(self, name, command, device_type="*"):
        self.name = name
        self.command = command
        self.device_type = device_type  # '*' for all devices
        
    def to_dict(self):
        return {
            "name": self.name,
            "command": self.command,
            "device_type": self.device_type
        }
        
    @staticmethod
    def from_dict(data):
        return DeviceCommand(data["name"], data["command"], data.get("device_type", "*"))
