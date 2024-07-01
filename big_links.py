import os
import shutil
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QInputDialog, QProgressBar, QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

class WorkerThread(QThread):
    update_progress = pyqtSignal(int)
    finalize_operation = pyqtSignal(str, bool)

    def __init__(self, source_path, target_path, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.target_path = target_path
        self.moved_files = []

    def run(self):
        logging.info(f"WorkerThread started with source: {self.source_path} and target: {self.target_path}")
        if not is_admin():
            logging.error("Admin privileges required.")
            self.finalize_operation.emit("Admin privileges required.", False)
            return

        if os.listdir(self.target_path):
            logging.info("Target directory is not empty.")
            self.finalize_operation.emit("Target directory is not empty.", False)
            return

        try:
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
        except Exception as e:
            logging.error(f"Operation failed: {e}")
            self.finalize_operation.emit(f"Operation failed: {e}", False)

class SymbolicLinkerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.source_path = None
        self.target_path = None
        self.moved_files = []
        self.initUI()

    def initUI(self):
        logging.info("Initializing SymbolicLinkerWidget UI.")
        main_layout = QVBoxLayout()

        self.path_display = QLabel('Source: None\nTarget: None')
        main_layout.addWidget(self.path_display)
        self.message_container = QLabel('Hi!! Big links make big chains')
        main_layout.addWidget(self.message_container)
        
        self.select_source_button = QPushButton('Select Source Directory')
        self.select_source_button.clicked.connect(self.select_source_directory)
        main_layout.addWidget(self.select_source_button)

        self.select_target_button = QPushButton('Select Target Directory')
        self.select_target_button.clicked.connect(self.select_target_directory)
        main_layout.addWidget(self.select_target_button)

        self.start_move_button = QPushButton('Start Move/Symlink Operation')
        self.start_move_button.clicked.connect(self.move_contents_and_create_symlink)
        self.start_move_button.setEnabled(False)
        main_layout.addWidget(self.start_move_button)

        self.remove_symlink_button = QPushButton('Remove Symlink')
        self.remove_symlink_button.clicked.connect(self.remove_symlink)
        self.remove_symlink_button.setEnabled(False)
        main_layout.addWidget(self.remove_symlink_button)

        self.rollback_button = QPushButton('Undo move if failed symlink creation')
        self.rollback_button.clicked.connect(self.undo_move)
        self.rollback_button.setEnabled(False)
        main_layout.addWidget(self.rollback_button)

        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.setLayout(main_layout)

    def select_source_directory(self):
        self.source_path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        self.update_button_states()
        self.update_path_display()

    def select_target_directory(self):
        self.target_path = QFileDialog.getExistingDirectory(self, "Select Target Directory")
        self.update_button_states()
        self.update_path_display()

    def update_path_display(self):
        self.path_display.setText(f"Source: {self.source_path or 'None'}\nTarget: {self.target_path or 'None'}")
        paths_selected = self.source_path is not None and self.target_path is not None
        self.start_move_button.setEnabled(paths_selected)

    def update_button_states(self):
        paths_selected = self.source_path is not None and self.target_path is not None
        self.start_move_button.setEnabled(paths_selected)

    def move_contents_and_create_symlink(self):
        logging.info("Initiating move contents and create symlink operation.")
        self.disable_all_buttons()

        if not self.source_path or not self.target_path:
            logging.error("Source or target path is not specified.")
            self.show_error_popup("Source or target path is missing.")
            return

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
                return

        if not is_admin():
            logging.error("Admin privileges required to create symlinks.")
            self.show_error_popup("Admin privileges are required for this operation.")
            return

        try:
            self.worker_thread = WorkerThread(self.source_path, self.target_path)
            self.worker_thread.update_progress.connect(self.update_progress)
            self.worker_thread.finalize_operation.connect(self.finalize_operation)
            logging.info("Starting WorkerThread to move contents and create symlink.")
            self.worker_thread.start()
        except Exception as e:
            logging.error(f"Failed to start the operation: {e}")
            self.show_error_popup(f"Operation failed to start: {e}")

    def show_error_popup(self, message):
        QMessageBox.critical(self, "Operation Error", message)

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def finalize_operation(self, message, success):
        logging.info(f"Finalize operation received with message: {message}, success: {success}")
        self.message_container.setText(message)
        if success:
            self.progress_bar.setValue(0)
            self.remove_symlink_button.setEnabled(True)
            self.rollback_button.setEnabled(True)
        self.enable_buttons()

    def undo_move(self):
        if not self.source_path or not self.target_path or not hasattr(self, 'moved_files'):
            self.message_container.setText("Cannot undo move: missing source, target, or moved files list.")
            logging.info(f"Cannot undo move: missing source, target, or moved files list.")
            return

        try:
            os.makedirs(self.source_path, exist_ok=True)
            for item in self.moved_files:
                target_item_path = os.path.join(self.target_path, item)
                source_item_path = os.path.join(self.source_path, item)
                if os.path.exists(target_item_path):
                    shutil.move(target_item_path, source_item_path)

            self.message_container.setText("Move operation undone successfully.")
            logging.info(f"Move operation undone successfully.")
        except OSError as e:
            self.message_container.setText(f"Failed to undo move: {e}")
            logging.info(f"Failed to undo move: {e}")
        finally:
            self.rollback_button.setEnabled(False)

    def remove_symlink(self):
        if self.source_path and os.path.islink(self.source_path):
            try:
                os.unlink(self.source_path)
                self.message_container.setText("Symlink removed successfully.")
                self.remove_symlink_button.setEnabled(False)
                self.source_path = None
                logging.info(f"Removed Symlink")
            except OSError as e:
                self.message_container.setText(f"Failed to remove symlink: {e}")
                logging.info(f"Failed to remove symlink: {e}")
        else:
            self.message_container.setText("No symlink selected.")
            logging.info(f"No symlink selected.")

    def disable_all_buttons(self):
        self.start_move_button.setEnabled(False)
        self.remove_symlink_button.setEnabled(False)
        self.rollback_button.setEnabled(False)

    def enable_buttons(self):
        self.update_button_states()
        self.remove_symlink_button.setEnabled(True)
        self.rollback_button.setEnabled(True)
