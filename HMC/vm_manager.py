import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel
from PyQt6.QtCore import pyqtSignal
from HMC.firecracker_manager import FirecrackerManager
from HMC.vault_manager import VaultManager
import os

class VMManagerWidget(QWidget):
    vm_status_changed = pyqtSignal(str, str)  # VM name, new status

    def __init__(self):
        super().__init__()
        self.fc_manager = FirecrackerManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # VM List
        self.vm_list = QListWidget()
        layout.addWidget(QLabel("VMs:"))
        layout.addWidget(self.vm_list)

        # VM Controls
        controls_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create VM")
        self.start_btn = QPushButton("Start VM")
        self.stop_btn = QPushButton("Stop VM")
        controls_layout.addWidget(self.create_btn)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        layout.addLayout(controls_layout)

        # VM Creation inputs
        create_layout = QHBoxLayout()
        self.vm_name_input = QLineEdit()
        self.vm_name_input.setPlaceholderText("VM Name")
        self.kernel_input = QLineEdit()
        self.kernel_input.setPlaceholderText("Kernel Image Path")
        self.rootfs_input = QLineEdit()
        self.rootfs_input.setPlaceholderText("Rootfs Image Path")
        create_layout.addWidget(self.vm_name_input)
        create_layout.addWidget(self.kernel_input)
        create_layout.addWidget(self.rootfs_input)
        layout.addLayout(create_layout)

        self.setLayout(layout)

        # Connect signals
        self.create_btn.clicked.connect(self.create_vm)
        self.start_btn.clicked.connect(self.start_vm)
        self.stop_btn.clicked.connect(self.stop_vm)
        self.vm_list.itemSelectionChanged.connect(self.update_buttons)

        self.update_vm_list()

    def create_vm(self):
        vm_name = self.vm_name_input.text()
        kernel_image = self.kernel_input.text()
        rootfs_image = self.rootfs_input.text()
        self.fc_manager.create_vm(vm_name, kernel_image, rootfs_image)
        self.update_vm_list()
        self.vm_status_changed.emit(vm_name, "created")

    def start_vm(self):
        selected_items = self.vm_list.selectedItems()
        if selected_items:
            vm_name = selected_items[0].text()
            self.fc_manager.start_vm(vm_name)
            self.update_vm_list()
            self.vm_status_changed.emit(vm_name, "running")

    def stop_vm(self):
        selected_items = self.vm_list.selectedItems()
        if selected_items:
            vm_name = selected_items[0].text()
            self.fc_manager.stop_vm(vm_name)
            self.update_vm_list()
            self.vm_status_changed.emit(vm_name, "stopped")

    def update_vm_list(self):
        self.vm_list.clear()
        for vm_name in self.fc_manager.list_vms():
            state = self.fc_manager.get_vm_state(vm_name)
            self.vm_list.addItem(f"{vm_name} ({state})")

    def update_buttons(self):
        selected_items = self.vm_list.selectedItems()
        if selected_items:
            vm_name = selected_items[0].text().split(" ")[0]
            state = self.fc_manager.get_vm_state(vm_name)
            self.start_btn.setEnabled(state != "running")
            self.stop_btn.setEnabled(state == "running")
        else:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

class VMManager:
    def __init__(self, vault_manager):
        self.vbox = None
        self.vault_manager = vault_manager
        self.iso_folder = self.vault_manager.get_iso_folder()

    def list_vms(self):
        return [machine.name for machine in self.vbox.machines]

    def start_vm(self, vm_name):
        try:
            machine = self.vbox.find_machine(vm_name)
         #   session = virtualbox.Session()
         ###   progress = machine.launch_vm_process(session, "gui", [])
         ###   progress.wait_for_completion(60000)
            print(f"Started VM: {vm_name}")
        except Exception as e:
            print(f"Error starting VM {vm_name}: {str(e)}")

    def stop_vm(self, vm_name):
        try:
            machine = self.vbox.find_machine(vm_name)
            session = machine.create_session()
            progress = session.console.power_down()
            progress.wait_for_completion(60000)
            print(f"Stopped VM: {vm_name}")
        except Exception as e:
            print(f"Error stopping VM {vm_name}: {str(e)}")

    def get_vm_state(self, vm_name):
        try:
            machine = self.vbox.find_machine(vm_name)
            return machine.state
        except Exception as e:
            print(f"Error getting state for VM {vm_name}: {str(e)}")
            return None

    def create_vm(self, vm_name, os_type="Other", iso_name=None):
        try:
            machine = self.vbox.create_machine("", vm_name, [], os_type, "")
            self.vbox.register_machine(machine)
            
            if iso_name:
                iso_path = os.path.join(self.iso_folder, iso_name)
                if os.path.exists(iso_path):
                    # Attach the ISO to the VM (you'll need to implement this part)
                    self.attach_iso_to_vm(machine, iso_path)
                else:
                    print(f"Warning: ISO file {iso_name} not found in the ISO folder.")
            
            print(f"Created VM: {vm_name}")
        except Exception as e:
            print(f"Error creating VM {vm_name}: {str(e)}")

    def attach_iso_to_vm(self, machine, iso_path):
        # Implement the logic to attach an ISO to a VM
        # This will depend on the virtualization technology you're using
        pass

    def list_available_isos(self):
        return [f for f in os.listdir(self.iso_folder) if f.endswith('.iso')]

    def delete_vm(self, vm_name):
        try:
            machine = self.vbox.find_machine(vm_name)
            machine.remove(delete=True)
            print(f"Deleted VM: {vm_name}")
        except Exception as e:
            print(f"Error deleting VM {vm_name}: {str(e)}")

    def run_command_in_vm(self, vm_name, command):
        try:
            machine = self.vbox.find_machine(vm_name)
            session = machine.create_session()
            guest_session = session.console.guest.create_session("user", "password")
            process, stdout, stderr = guest_session.execute(command)
            print(f"Command output: {stdout}")
            guest_session.close()
            session.unlock_machine()
        except Exception as e:
            print(f"Error running command in VM {vm_name}: {str(e)}")

# Example usage
if __name__ == "__main__":
    vault_manager = VaultManager()  # You'll need to properly initialize this
    vm_manager = VMManager(vault_manager)

    print("Available ISOs:")
    print(vm_manager.list_available_isos())

    vm_name = "TestVM"
    iso_name = "qubes-os-4.1-template-fedora-38-amd64.iso"  # Assuming this ISO is in the folder
    
    vm_manager.create_vm(vm_name, os_type="Qubes OS 4.1", iso_name=iso_name)
    time.sleep(2)  # Wait for VM creation to complete

    vm_manager.start_vm(vm_name)
    time.sleep(10)  # Wait for VM to start

    print(f"VM State: {vm_manager.get_vm_state(vm_name)}")

    vm_manager.run_command_in_vm(vm_name, "echo Hello from VM")

    vm_manager.stop_vm(vm_name)
    time.sleep(5)  # Wait for VM to stop

    vm_manager.delete_vm(vm_name)
