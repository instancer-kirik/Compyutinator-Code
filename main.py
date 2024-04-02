import os
import sys
import shutil
import logging
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,QInputDialog, QProgressBar, QFileDialog, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal



log_directory = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_directory):
    os.makedirs(log_directory)  # Ensure the directory exists

log_file_path = os.path.join(log_directory, 'app.log')


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file_path, 'a'), logging.StreamHandler()])

# For debugging, choose a specific, writable path, e.g., current working directory or a subdirectory like 'logs'

# Test logging
logging.info("Application started")
def is_admin():
    """Check if the program has admin privileges."""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
class WorkerThread(QThread):
    update_progress = pyqtSignal(int)
    finalize_operation = pyqtSignal(str, bool)  # Include success status

    def __init__(self, source_path, target_path, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.target_path = target_path

    def run(self):
        logging.info(f"WorkerThread started with source: {self.source_path} and target: {self.target_path}")
        if not is_admin():  # Assuming is_admin() is defined as shown earlier
            logging.error("Admin privileges required.")
            self.finalize_operation.emit("Admin privileges required.", False)
            return

        # Check if target directory is empty
        if os.listdir(self.target_path):
            logging.info("Target directory is not empty.")
            self.finalize_operation.emit("Target directory is not empty.", False)
            return

        try:
            # Proceed with the file move and symlink creation
            # Ensure moved_files is used to track moved items for potential rollback
            logging.info(f"Moving files from {self.source_path} to {self.target_path}")
            # File move operations and symlink creation here
            
            self.moved_files = []
            total_files = len(os.listdir(self.source_path))
            moved_files_count = 0

            for item in os.listdir(self.source_path):
                source_item_path = os.path.join(self.source_path, item)
                target_item_path = os.path.join(self.target_path, item)
                shutil.move(source_item_path, target_item_path)
                self.moved_files.append(item)
                moved_files_count += 1
                progress = int((moved_files_count / total_files) * 100)
                self.update_progress.emit(progress)

            # Remove the source directory and create a symlink
            try:
                os.rmdir(self.source_path)
                logging.info(f"Source directory {self.source_path} removed successfully.")
                try:
                    os.symlink(self.target_path, self.source_path)
                    logging.info(f"Symlink created from {self.source_path} to {self.target_path}.")
                    self.finalize_operation.emit("Operation completed successfully.", True)
                except OSError as e:
                    logging.error(f"Failed to create symlink: {e}")
                    self.finalize_operation.emit(f"Failed to create symlink: {e}", False)
            except OSError as e:
                logging.error(f"Failed to remove source directory: {e}")
                self.finalize_operation.emit(f"Failed to remove source directory: {e}", False)
            # self.finalize_operation.emit("Contents moved and symlink created.")
            
       
        except Exception as e:
            logging.error(f"Operation failed: {e}")
            self.finalize_operation.emit(f"Operation failed: {e}", False)
        
        
class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('BigLinks')
        self.source_path = None
        self.target_path = None
        self.moved_files = []
        self.initUI()
    def initUI(self):
        logging.info("Init method test starting.")
        main_layout = QVBoxLayout()
         # Display for source and target paths
        self.path_display = QLabel('Source: None\nTarget: None')
        main_layout.addWidget(self.path_display)
        self.message_container = QLabel('Hi!! Big links make big chains')
        main_layout.addWidget(self.message_container)
        # Source selection button
        self.select_source_button = QPushButton('Select Source Directory')
        self.select_source_button.clicked.connect(self.select_source_directory)
        main_layout.addWidget(self.select_source_button)

        # Target selection button
        self.select_target_button = QPushButton('Select Target Directory')
        self.select_target_button.clicked.connect(self.select_target_directory)
        main_layout.addWidget(self.select_target_button)

         # Operation buttons
        self.start_move_button = QPushButton('Start Move/Symlink Operation')
        self.start_move_button.clicked.connect(self.move_contents_and_create_symlink)
        self.start_move_button.setEnabled(False)  # Disabled until paths are selected
        main_layout.addWidget(self.start_move_button)

        self.remove_symlink_button = QPushButton('Remove Symlink')
        self.remove_symlink_button.clicked.connect(self.remove_symlink)
        self.remove_symlink_button.setEnabled(False)  # Disabled initially
        main_layout.addWidget(self.remove_symlink_button)

        self.rollback_button = QPushButton('Undo move if failed symlink creation')
        self.rollback_button.clicked.connect(self.undo_move)
        self.rollback_button.setEnabled(False)  # Disabled initially
        main_layout.addWidget(self.rollback_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def select_source_directory(self):
        self.source_path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if self.source_path:
            print(f"Selected source directory: {self.source_path}")
            # Additional logic to handle source directory selection
        self.update_button_states()
        self.update_path_display()
    def select_target_directory(self):
        self.target_path = QFileDialog.getExistingDirectory(self, "Select Target Directory")
        if self.target_path:
            print(f"Selected target directory: {self.target_path}")
            # Additional logic to handle target directory selection
        self.update_button_states()
        self.update_path_display()
    def update_path_display(self):
        self.path_display.setText(f"Source: {self.source_path or 'None'}\nTarget: {self.target_path or 'None'}")
        paths_selected = self.source_path is not None and self.target_path is not None
        self.start_move_button.setEnabled(paths_selected)

    def on_navigate_pressed(self, instance,path):
        self.file_picker.navigate(path)
    def update_button_states(self):
    # Example logic to update button states
        paths_selected = self.source_path is not None and self.target_path is not None
        self.start_move_button.setEnabled(paths_selected)
    
    def navigate_to_path(self, instance):
        """Navigate the file chooser to the path entered by the user."""
        path = self.path_input.text.strip()
        if os.path.isdir(path):
            self.file_chooser.path = path
        else:
            self.message_container.text = "Invalid path. Please enter a valid directory path."
    def select_link_source(self, instance):
        selected = self.file_chooser.selection[0] if self.file_chooser.selection else self.file_chooser.path
        if os.path.islink(selected):
            print(f"Selected simlink: {selected}")
            self.symlink_source = selected
            # Show that the source is a symlink and display its target
            symlink_target = os.readlink(selected)
            self.message_container.text = f"Source is a symlink pointing to: {symlink_target}\nConsider removing the symlink."
            self.remove_symlink_button.disabled = False  # Enable the button to remove the symlink
        else:
            self.source_path = selected
            self.update_path_label()
            self.remove_symlink_button.disabled = True  # Disable the button as it's not a symlink
        
  
    def select_link_target(self, instance):
        # Similar logic applied to selecting the target
        selected = self.file_chooser.selection[0] if self.file_chooser.selection else self.file_chooser.path
    # Check if the selected path is a symlink
        if os.path.islink(selected):
            # Update the UI or notify the user that the selected source is a symlink
            # and suggest removing the link
            print(f"Selected source directory: {selected}")
            self.message_container.text = "Selected target is a symlink. Consider removing the link."
            # Optionally, store the symlink path or set a flag here if you need to act on this information later
            self.symlink_source = selected
        else:
             # Update the target path
            self.target_path = selected
            self.update_path_label()
       
        
    def update_path_label(self):
        # Update the label to show the selected source and target paths
        self.message_container.text = f"Source: {self.source_path or 'Not selected'}\nTarget: {self.target_path or 'Not selected'}"
        # Additional UI feedback for confirmation, if necessary
        if self.source_path:
            print(f"Selected source directory: {self.source_path}")
        if self.target_path:
            print(f"Selected target directory: {self.target_path}")
    def get_drives(self):
        """List all available drives on Windows."""
        drives = [f"{drive}:\\" for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{drive}:\\")]
        return drives

    def on_drive_selection(self, spinner, text):
        """Update the file chooser path based on selected drive."""
        if text:  # Ensure the text is not empty
            #print(f"Attempting to set file chooser path to: {text}")
            try:
                # Attempt to change the directory to verify the path
                os.chdir(text)  # Use the text directly since it's already correctly formatted
                # If successful, update the file chooser's path
                self.file_chooser.path = text
                #print(f"Successfully updated file chooser path to: {text}")
            except FileNotFoundError:
                print(f"The drive or path {text} does not exist.")
            except Exception as e:
                print(f"Error changing directory: {e}")
        else:
            print("No drive selected.")
    def update_message_container(self, instance):
        # Update the label based on selection
        if self.file_chooser.selection:
            selected_path = self.file_chooser.selection[0]
            if os.path.islink(selected_path):
                target_path = os.readlink(selected_path)
                self.message_container.text = f"Symlink target: {target_path}"
            else:
                self.message_container.text = f"Selected path: {selected_path}"
        else:
            self.message_container.text = "Selected path: None"
    
   
    def get_directory_size(start_path):
        """Returns the total size of all files in start_path and its subdirectories."""
        total_size = 0
        for dirpath, _dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    def get_free_space(path):
        """Returns the free space of the drive containing 'path'."""
        _total, _used, free = shutil.disk_usage(os.path.dirname(path))
        return free
    
    def move_contents_and_create_symlink(self):
        logging.info("Initiating move contents and create symlink operation.")
        self.disable_all_buttons()  # Prevent further actions during the operation

        if not self.source_path or not self.target_path:
            logging.error("Source or target path is not specified.")
            self.show_error_popup("Source or target path is missing.")
            return

        # Check for non-empty target directory
        if os.listdir(self.target_path):
            new_folder_name, ok = QInputDialog.getText(self, "Non-Empty Target Directory",
                                                    "The target directory is not empty. Enter a new folder name to create within the target directory, or cancel to abort the operation:")
            if ok and new_folder_name:
                new_target_path = os.path.join(self.target_path, new_folder_name)
                try:
                    os.makedirs(new_target_path, exist_ok=True)
                    logging.info(f"New target directory created: {new_target_path}")
                    self.target_path = new_target_path
                except Exception as e:
                    logging.error(f"Failed to create new target directory: {e}")
                    self.show_error_popup(f"Failed to create new target directory: {e}")
                    return
            else:
                logging.info("Operation aborted by the user.")
                return  # Abort if the user cancels or enters no name

        # Admin privilege check (for operations like creating symlinks)
        if not is_admin():
            logging.error("Admin privileges required to create symlinks.")
            self.show_error_popup("Admin privileges are required for this operation.")
            return

        try:
            self.worker_thread = WorkerThread(self.source_path, self.target_path)
            self.worker_thread.update_progress.connect(self._update_progress)
            self.worker_thread.finalize_operation.connect(self._finalize_operation)
            logging.info("Starting WorkerThread to move contents and create symlink.")
            self.worker_thread.start()
        except Exception as e:
            logging.error(f"Failed to start the operation: {e}")
            self.show_error_popup(f"Operation failed to start: {e}")

    def show_error_popup(self, message):
        QMessageBox.critical(self, "Operation Error", message)
       
    def _update_progress(self, progress):
        self.progress_bar.value = progress
    def _enable_undo_button(self, *_args):
        self.rollback_button.disabled = False
    def _finalize_operation(self, message,success):
        logging.info(f"Finalize operation received with message: {message}, success: {success}")
        self.message_container.text = message 
        if success:
            self.progress_bar.value = 0
           
            self.remove_symlink_button.setEnabled(True)
            self.rollback_button.setEnabled(True)
            pass  # Update UI, logging, etc.
        else:
            # Handle failure
            pass  # Update UI, logging, etc. Show error message, etc.
            # Reset progress bar for next operation
        
            # Your logic to remove the directory and create a symlink here
    def undo_move(self, instance):
        if not self.source_path or not self.target_path or not hasattr(self, 'moved_files'):
            self.message_container.text = "Cannot undo move: missing source, target, or moved files list."
            return

        try:
            os.makedirs(self.source_path, exist_ok=True)  # Ensure the source directory exists
            
            # Move only the tracked files back to the source directory
            for item in self.moved_files:
                target_item_path = os.path.join(self.target_path, item)
                source_item_path = os.path.join(self.source_path, item)
                if os.path.exists(target_item_path):  # Check if the item still exists in the target
                    shutil.move(target_item_path, source_item_path)
            
            self.message_container.text = "Move operation undone successfully."
        except OSError as e:
            self.message_container.text = f"Failed to undo move: {e}"
        finally:
            self.rollback_button.disabled = True  # Disable the undo button to prevent repeated undos
    def remove_symlink(self, instance):
        if self.source_path and os.path.islink(self.source_path):
            try:
                os.unlink(self.source_path)
                self.message_container.text = "Symlink removed successfully."
                self.remove_symlink_button.disabled = True  # Disable the button after removal
                self.source_path = None  # Clear the source path
            except OSError as e:
                self.message_container.text = f"Failed to remove symlink: {e}"
        else:
            self.message_container.text = "No symlink selected."

    
    def disable_all_buttons(self):
        # Helper method to disable all operation buttons
        self.start_move_button.setEnabled(False)
        self.remove_symlink_button.setEnabled(False)
        self.rollback_button.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())