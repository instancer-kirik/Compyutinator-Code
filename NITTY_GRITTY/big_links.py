import os
import shutil
import logging
import stat
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QInputDialog, QProgressBar, QFileDialog, QMessageBox, QTreeView, QStyle, QStyledItemDelegate
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex
from PyQt6.QtGui import QFileSystemModel, QIcon, QPainter
from NITTY_GRITTY.ThreadTrackers import SafeQThread

def is_admin():
    try:
        # Linux/Unix check
        if os.name == 'posix':
            return os.geteuid() == 0
        # Windows check
        else:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.error(f"Failed to check admin status: {e}")
        return False

class WorkerThread(SafeQThread):
    update_progress = pyqtSignal(int)
    finalize_operation = pyqtSignal(str, bool)

    def __init__(self, source_path, target_path, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.target_path = target_path
        self.moved_files = []

    def run(self):
        logging.info(f"WorkerThread started with source: {self.source_path} and target: {self.target_path}")
        
        # Validate paths
        if not os.path.exists(self.source_path):
            self.finalize_operation.emit("Source directory does not exist.", False)
            return
        if not os.path.exists(self.target_path):
            self.finalize_operation.emit("Target directory does not exist.", False)
            return

        # Check write permissions
        if not os.access(os.path.dirname(self.source_path), os.W_OK):
            self.finalize_operation.emit("No write permission in source directory parent.", False)
            return
        if not os.access(self.target_path, os.W_OK):
            self.finalize_operation.emit("No write permission in target directory.", False)
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
                
                # Handle symlink creation based on OS
                if os.name == 'posix':
                    # Ensure proper permissions on Linux
                    os.symlink(self.target_path, self.source_path)
                    # Make symlink readable by all users
                    os.chmod(self.source_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                                                    stat.S_IRGRP | stat.S_IXGRP |
                                                    stat.S_IROTH | stat.S_IXOTH)
                else:
                    # Windows might need admin rights
                    os.symlink(self.target_path, self.source_path, target_is_directory=True)
                
                logging.info(f"Symlink created from {self.source_path} to {self.target_path}.")
                self.finalize_operation.emit("Operation completed successfully.", True)
            except OSError as e:
                logging.error(f"Failed to create symlink: {e}")
                self.finalize_operation.emit(f"Failed to create symlink: {e}", False)
                # Attempt to restore the source directory
                self.undo_move()
        except Exception as e:
            logging.error(f"Operation failed: {e}")
            self.finalize_operation.emit(f"Operation failed: {e}", False)

class PermissionDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.readable_icon = self.parent().style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        self.not_readable_icon = self.parent().style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.writable_icon = self.parent().style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.symlink_icon = self.parent().style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        super().paint(painter, option, index)
        
        file_path = self.parent().model().filePath(index)
        icon_size = 16
        x = option.rect.right() - icon_size * 3
        y = option.rect.center().y() - icon_size // 2

        # Draw read permission icon
        if os.access(file_path, os.R_OK):
            self.readable_icon.paint(painter, x, y, icon_size, icon_size)
        else:
            self.not_readable_icon.paint(painter, x, y, icon_size, icon_size)

        # Draw write permission icon
        if os.access(file_path, os.W_OK):
            self.writable_icon.paint(painter, x + icon_size, y, icon_size, icon_size)

        # Draw symlink icon
        if os.path.islink(file_path):
            self.symlink_icon.paint(painter, x + icon_size * 2, y, icon_size, icon_size)

class FileExplorerWidget(QTreeView):
    path_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.setModel(self.model)
        
        # Hide unnecessary columns and set proper width
        self.setColumnWidth(0, 250)
        for col in range(1, self.model.columnCount()):
            self.hideColumn(col)

        # Set item delegate for permission icons
        self.setItemDelegate(PermissionDelegate(self))
        
        # Enable selection and drag-drop
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        index = self.currentIndex()
        if index.isValid():
            path = self.model.filePath(index)
            self.path_selected.emit(path)

class SymbolicLinkerWidget(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.source_path = None
        self.target_path = None
        self.moved_files = []
        self.initUI()

    def initUI(self):
        logging.info("Initializing SymbolicLinkerWidget UI.")
        main_layout = QVBoxLayout()

        # Add header with instructions
        header_label = QLabel("Select source and target directories to create a symbolic link")
        header_label.setStyleSheet("font-weight: bold; padding: 5px;")
        main_layout.addWidget(header_label)

        # Create horizontal layout for dual file explorers
        explorer_layout = QHBoxLayout()

        # Source file explorer
        source_group = QVBoxLayout()
        source_label = QLabel("Source Directory:")
        self.source_explorer = FileExplorerWidget()
        self.source_explorer.path_selected.connect(self.set_source_path)
        source_group.addWidget(source_label)
        source_group.addWidget(self.source_explorer)
        explorer_layout.addLayout(source_group)

        # Target file explorer
        target_group = QVBoxLayout()
        target_label = QLabel("Target Directory:")
        self.target_explorer = FileExplorerWidget()
        self.target_explorer.path_selected.connect(self.set_target_path)
        target_group.addWidget(target_label)
        target_group.addWidget(self.target_explorer)
        explorer_layout.addLayout(target_group)

        main_layout.addLayout(explorer_layout)

        # Add path display
        self.path_display = QLabel('Source: None\nTarget: None')
        self.path_display.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        main_layout.addWidget(self.path_display)

        # Add message container
        self.message_container = QLabel('Select directories to begin')
        self.message_container.setStyleSheet("color: #666; padding: 5px;")
        main_layout.addWidget(self.message_container)

        # Create button layout
        button_layout = QHBoxLayout()

        # Add operation buttons
        self.start_move_button = QPushButton('Create Symlink')
        self.start_move_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon))
        self.start_move_button.clicked.connect(self.move_contents_and_create_symlink)
        self.start_move_button.setEnabled(False)
        button_layout.addWidget(self.start_move_button)

        self.remove_symlink_button = QPushButton('Remove Symlink')
        self.remove_symlink_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.remove_symlink_button.clicked.connect(self.remove_symlink)
        self.remove_symlink_button.setEnabled(False)
        button_layout.addWidget(self.remove_symlink_button)

        self.rollback_button = QPushButton('Undo Operation')
        self.rollback_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.rollback_button.clicked.connect(self.undo_move)
        self.rollback_button.setEnabled(False)
        button_layout.addWidget(self.rollback_button)

        main_layout.addLayout(button_layout)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 20px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # Add permission legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend:"))
        legend_layout.addWidget(QLabel("✓ Readable"))
        legend_layout.addWidget(QLabel("💾 Writable"))
        legend_layout.addWidget(QLabel("🔗 Symlink"))
        legend_layout.addStretch()
        main_layout.addLayout(legend_layout)

        self.setLayout(main_layout)

    def set_source_path(self, path):
        self.source_path = path
        self.update_button_states()
        self.update_path_display()

    def set_target_path(self, path):
        self.target_path = path
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
