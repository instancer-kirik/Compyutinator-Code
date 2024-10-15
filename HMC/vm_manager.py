import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal
import virtualbox
import os

class VMManagerWidget(QWidget):
    vm_status_changed = pyqtSignal(str, str)  # VM name, new status

    def __init__(self, vault_manager):
        super().__init__()
        self.vm_manager = VMManager(vault_manager)
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
        self.os_type_combo = QComboBox()
        self.os_type_combo.addItems(["Other", "Windows", "Linux"])
        self.iso_combo = QComboBox()
        self.iso_combo.addItems(["<No ISO>"] + self.vm_manager.list_available_isos())
        create_layout.addWidget(self.vm_name_input)
        create_layout.addWidget(self.os_type_combo)
        create_layout.addWidget(self.iso_combo)
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
        os_type = self.os_type_combo.currentText()
        iso_name = self.iso_combo.currentText() if self.iso_combo.currentText() != "<No ISO>" else None
        self.vm_manager.create_vm(vm_name, os_type, iso_name)
        self.update_vm_list()
        self.vm_status_changed.emit(vm_name, "created")

    def start_vm(self):
        selected_items = self.vm_list.selectedItems()
        if selected_items:
            vm_name = selected_items[0].text().split(" ")[0]
            self.vm_manager.start_vm(vm_name)
            self.update_vm_list()
            self.vm_status_changed.emit(vm_name, "running")

    def stop_vm(self):
        selected_items = self.vm_list.selectedItems()
        if selected_items:
            vm_name = selected_items[0].text().split(" ")[0]
            self.vm_manager.stop_vm(vm_name)
            self.update_vm_list()
            self.vm_status_changed.emit(vm_name, "stopped")

    def update_vm_list(self):
        self.vm_list.clear()
        for vm_name in self.vm_manager.list_vms():
            state = self.vm_manager.get_vm_state(vm_name)
            self.vm_list.addItem(f"{vm_name} ({state})")

    def update_buttons(self):
        selected_items = self.vm_list.selectedItems()
        if selected_items:
            vm_name = selected_items[0].text().split(" ")[0]
            state = self.vm_manager.get_vm_state(vm_name)
            self.start_btn.setEnabled(state != "Running")
            self.stop_btn.setEnabled(state == "Running")
        else:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

class VMManager:
    def __init__(self, vault_manager):
        self.vbox = virtualbox.VirtualBox()
        self.vault_manager = vault_manager
        self.iso_folder = self.vault_manager.get_iso_folder()

    def list_vms(self):
        return [machine.name for machine in self.vbox.machines]

    def start_vm(self, vm_name):
        try:
            machine = self.vbox.find_machine(vm_name)
            session = virtualbox.Session()
            progress = machine.launch_vm_process(session, "gui", [])
            progress.wait_for_completion(60000)
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
            return str(machine.state)
        except Exception as e:
            print(f"Error getting state for VM {vm_name}: {str(e)}")
            return None

    def create_vm(self, vm_name, os_type="Other", iso_name=None):
        try:
            machine = self.vbox.create_machine("", vm_name, [], os_type, "")
            self.vbox.register_machine(machine)
            
            session = machine.create_session()
            
            # Set memory and CPU
            session.machine.memory_size = 1024  # 1 GB RAM
            session.machine.cpu_count = 1

            # Create and attach a virtual hard disk
            hdd = self.vbox.create_medium("vdi", f"{vm_name}.vdi", virtualbox.AccessMode.read_write, virtualbox.DeviceType.hard_disk)
            progress = hdd.create_base_storage(10 * 1024 * 1024 * 1024)  # 10 GB
            progress.wait_for_completion(60000)
            session.machine.attach_device("SATA Controller", 0, 0, virtualbox.DeviceType.hard_disk, hdd)

            if iso_name:
                iso_path = os.path.join(self.iso_folder, iso_name)
                if os.path.exists(iso_path):
                    self.attach_iso_to_vm(session.machine, iso_path)
                else:
                    print(f"Warning: ISO file {iso_name} not found in the ISO folder.")
            
            session.machine.save_settings()
            session.unlock_machine()
            
            print(f"Created VM: {vm_name}")
        except Exception as e:
            print(f"Error creating VM {vm_name}: {str(e)}")

    def attach_iso_to_vm(self, machine, iso_path):
        try:
            session = machine.create_session()
            session.machine.attach_device("IDE Controller", 1, 0, virtualbox.DeviceType.dvd, None)
            dvd = session.machine.get_medium("IDE Controller", 1, 0)
            dvd.host_drive = iso_path
            session.machine.save_settings()
            session.unlock_machine()
        except Exception as e:
            print(f"Error attaching ISO to VM: {str(e)}")

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
    from PyQt6.QtWidgets import QApplication
    import sys
    from HMC.vault_manager import VaultManager

    app = QApplication(sys.argv)
    vault_manager = VaultManager()  # You'll need to properly initialize this
    vm_widget = VMManagerWidget(vault_manager)
    vm_widget.show()
    sys.exit(app.exec())
