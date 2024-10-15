import requests
import json
import subprocess
import os
import time

class FirecrackerManager:
    def __init__(self):
        self.api_socket = "/tmp/firecracker.socket"
        self.vms = {}

    def _send_request(self, method, endpoint, data=None):
        url = f"http+unix://{self.api_socket.replace('/', '%2F')}{endpoint}"
        response = requests.request(method, url, json=data)
        return response

    def create_vm(self, vm_name, kernel_image, rootfs_image):
        if vm_name in self.vms:
            print(f"VM {vm_name} already exists")
            return

        config = {
            "boot-source": {
                "kernel_image_path": kernel_image,
                "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
            },
            "drives": [
                {
                    "drive_id": "rootfs",
                    "path_on_host": rootfs_image,
                    "is_root_device": True,
                    "is_read_only": False
                }
            ],
            "machine-config": {
                "vcpu_count": 1,
                "mem_size_mib": 128
            }
        }

        response = self._send_request("PUT", "/machine-config", config)
        if response.status_code == 204:
            self.vms[vm_name] = {"status": "created"}
            print(f"Created VM: {vm_name}")
        else:
            print(f"Error creating VM {vm_name}: {response.text}")

    def start_vm(self, vm_name):
        if vm_name not in self.vms:
            print(f"VM {vm_name} not found")
            return

        response = self._send_request("PUT", "/actions", {"action_type": "InstanceStart"})
        if response.status_code == 204:
            self.vms[vm_name]["status"] = "running"
            print(f"Started VM: {vm_name}")
        else:
            print(f"Error starting VM {vm_name}: {response.text}")

    def stop_vm(self, vm_name):
        if vm_name not in self.vms:
            print(f"VM {vm_name} not found")
            return

        response = self._send_request("PUT", "/actions", {"action_type": "SendCtrlAltDel"})
        if response.status_code == 204:
            self.vms[vm_name]["status"] = "stopped"
            print(f"Stopped VM: {vm_name}")
        else:
            print(f"Error stopping VM {vm_name}: {response.text}")

    def get_vm_state(self, vm_name):
        if vm_name not in self.vms:
            print(f"VM {vm_name} not found")
            return None
        return self.vms[vm_name]["status"]

    def list_vms(self):
        return list(self.vms.keys())