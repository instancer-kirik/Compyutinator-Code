import os
import shutil
import logging
import stat
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QInputDialog, QProgressBar, QFileDialog, QMessageBox, 
    QTreeView, QStyle, QStyledItemDelegate, QTextEdit, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex, QObject, QThread
from PyQt6.QtGui import QFileSystemModel, QIcon, QPainter, QColor, QBrush, QFont
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
            total_files = len([f for f in os.listdir(self.source_path) if os.path.isfile(os.path.join(self.source_path, f))])
            if total_files == 0:
                self.finalize_operation.emit("No files to move.", False)
                return
            moved_files_count = 0

            for item in os.listdir(self.source_path):
                source_item_path = os.path.join(self.source_path, item)
                target_item_path = os.path.join(self.target_path, item)
                if os.path.isfile(source_item_path):
                    shutil.move(source_item_path, target_item_path)
                    self.moved_files.append(item)
                    moved_files_count += 1
                    progress = int((moved_files_count / total_files) * 100)
                    self.update_progress.emit(progress)
                    logging.debug(f"Moved {item}: {moved_files_count}/{total_files}")

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

    def undo_move(self):
        """Helper method to undo the move operation if symlink creation fails"""
        try:
            if not os.path.exists(self.source_path):
                os.makedirs(self.source_path)
            for item in self.moved_files:
                target_item_path = os.path.join(self.target_path, item)
                source_item_path = os.path.join(self.source_path, item)
                if os.path.exists(target_item_path):
                    shutil.move(target_item_path, source_item_path)
            logging.info("Move operation undone successfully")
            self.finalize_operation.emit("Move operation undone successfully.", False)
        except Exception as e:
            logging.error(f"Failed to undo move operation: {e}")
            self.finalize_operation.emit(f"Failed to undo move operation: {e}", False)

class SerializeWorker(QObject):
    serialization_done = pyqtSignal(str)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def serialize(self):
        try:
            logging.info(f"Starting serialization for path: {self.path}")
            context = {}
            total_dirs = 0
            total_files = 0
            for root, dirs, files in os.walk(self.path):
                total_dirs += len(dirs)
                total_files += len(files)

            processed_dirs = 0
            processed_files = 0

            for root, dirs, files in os.walk(self.path):
                rel_path = os.path.relpath(root, self.path)
                context[rel_path] = {
                    'directories': dirs,
                    'files': {file: os.path.getsize(os.path.join(root, file)) for file in files}
                }
                processed_dirs += len(dirs)
                processed_files += len(files)
                progress_percent = int(((processed_dirs + processed_files) / (total_dirs + total_files)) * 100) if (total_dirs + total_files) > 0 else 100
                self.progress.emit(progress_percent)
                logging.debug(f"Serialized {rel_path}: {progress_percent}% done")

            serialized_context = json.dumps(context, indent=4)
            logging.info(f"Serialization successful for path: {self.path}")
            self.serialization_done.emit(serialized_context)
        except Exception as e:
            logging.error(f"Failed to serialize directory context: {e}")
            self.error.emit(str(e))

class SnapshotWorker(QObject):
    snapshot_done = pyqtSignal(str)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, directories):
        super().__init__()
        self.directories = directories

    def snapshot(self):
        try:
            logging.info("Starting filesystem snapshot.")
            snapshot = {}
            total_dirs = len(self.directories)
            processed_dirs = 0

            for dir_info in self.directories:
                name = dir_info['name']
                path = dir_info['path']
                if os.path.exists(path):
                    serializer = SerializeWorker(path)
                    # Run serialization in a separate thread
                    serialization_thread = QThread()
                    serializer.moveToThread(serialization_thread)
                    serialization_thread.started.connect(serializer.serialize)
                    serializer.serialization_done.connect(lambda data, n=name: self.collect_snapshot(n, data))
                    serializer.progress.connect(self.update_progress)
                    serializer.error.connect(self.handle_error)
                    serializer.serialization_done.connect(serialization_thread.quit)
                    serializer.serialization_done.connect(serializer.deleteLater)
                    serialization_thread.finished.connect(serialization_thread.deleteLater)
                    serialization_thread.start()
                    serialization_thread.wait()  # Wait for serialization to finish
                processed_dirs += 1
                progress_percent = int((processed_dirs / total_dirs) * 100) if total_dirs > 0 else 100
                self.progress.emit(progress_percent)

            serialized_snapshot = json.dumps(snapshot, indent=4)
            logging.info("Filesystem snapshot created successfully.")
            self.snapshot_done.emit(serialized_snapshot)
        except Exception as e:
            logging.error(f"Failed to create filesystem snapshot: {e}")
            self.error.emit(str(e))

    def collect_snapshot(self, name, data):
        if 'snapshot' not in self.__dict__:
            self.snapshot = {}
        self.snapshot[name] = json.loads(data)

    def update_progress(self, progress_percent):
        self.progress.emit(progress_percent)

    def handle_error(self, error_message):
        self.error.emit(error_message)

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
        x = option.rect.right() - icon_size * 4
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

        # Optional: Change text color based on permissions or symlink status
        if os.path.islink(file_path):
            color = QColor('blue')  # Symlinks in blue
        elif not os.access(file_path, os.W_OK):
            color = QColor('gray')  # Read-only files in gray
        else:
            color = QColor('black')  # Regular files in black

        # Set painter font color
        painter.setPen(QPen(color))
        # Optionally, you can adjust the font style (e.g., italic for symlinks)
        font = QFont()
        if os.path.islink(file_path):
            font.setItalic(True)
        painter.setFont(font)

        # Draw the file name with the new color
        file_name = self.parent().model().fileName(index)
        painter.drawText(option.rect.left(), option.rect.top(), option.rect.width() - icon_size * 4, option.rect.height(), Qt.AlignmentFlag.AlignVCenter, file_name)

class FileExplorerWidget(QTreeView):
    path_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.setModel(self.model)
        self.setRootIndex(self.model.index(QDir.rootPath()))
        
        # Hide unnecessary columns and set proper width
        self.setColumnWidth(0, 250)
        for col in range(1, self.model.columnCount()):
            self.hideColumn(col)

        # Set item delegate for permission icons and colored text
        self.setItemDelegate(PermissionDelegate(self))
        
        # Enable selection and drag-drop
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        # Enable alternating row colors for better readability
        self.setAlternatingRowColors(True)

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

        # Add a new button for snapshotting filesystem
        self.snapshot_button = QPushButton('Snapshot Filesystem')
        self.snapshot_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self.snapshot_button.clicked.connect(self.snapshot_filesystem)
        button_layout.addWidget(self.snapshot_button)

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

        # Add context display area
        context_label = QLabel("Filesystem Context:")
        main_layout.addWidget(context_label)

        self.context_display = QTextEdit()
        self.context_display.setReadOnly(True)
        self.context_display.setFixedHeight(200)
        main_layout.addWidget(self.context_display)

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
            self.enable_buttons()
            return

        if os.listdir(self.target_path):
            new_folder_name, ok = QInputDialog.getText(
                self, 
                "Non-Empty Target Directory",
                "The target directory is not empty. Enter a new folder name to create within the target directory, or cancel to abort the operation:"
            )
            if ok and new_folder_name:
                new_target_path = os.path.join(self.target_path, new_folder_name)
                try:
                    os.makedirs(new_target_path, exist_ok=True)
                    logging.info(f"New target directory created: {new_target_path}")
                    self.target_path = new_target_path
                except Exception as e:
                    logging.error(f"Failed to create new target directory: {e}")
                    self.show_error_popup(f"Failed to create new target directory: {e}")
                    self.enable_buttons()
                    return
            else:
                logging.info("Operation aborted by the user.")
                self.message_container.setText("Operation aborted by the user.")
                self.enable_buttons()
                return

        if not is_admin():
            logging.error("Admin privileges required to create symlinks.")
            self.show_error_popup("Admin privileges are required for this operation.")
            self.enable_buttons()
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
            self.enable_buttons()

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
        self.snapshot_button.setEnabled(False)

    def enable_buttons(self):
        self.update_button_states()
        self.remove_symlink_button.setEnabled(True)
        self.rollback_button.setEnabled(True)
        self.snapshot_button.setEnabled(True)

    # --- New Functions ---

    def serialize_directory_context(self, path):
        """
        Serializes the directory context including file names and sizes.
        Returns a JSON string.
        """
        logging.info(f"Serializing context for path: {path}")
        context = {}
        try:
            for root, dirs, files in os.walk(path):
                rel_path = os.path.relpath(root, path)
                context[rel_path] = {
                    'directories': dirs,
                    'files': {file: os.path.getsize(os.path.join(root, file)) for file in files}
                }
            serialized_context = json.dumps(context, indent=4)
            logging.info(f"Serialization successful for path: {path}")
            return serialized_context
        except Exception as e:
            logging.error(f"Failed to serialize directory context: {e}")
            return json.dumps({"error": str(e)})

    def list_standard_directories(self):
        """
        Returns a list of standard directories based on the operating system.
        """
        logging.info("Listing standard directories.")
        standard_dirs = []
        try:
            home = os.path.expanduser("~")
            if os.name == 'nt':
                # Windows standard directories
                dirs = {
                    "Desktop": os.path.join(home, "Desktop"),
                    "Documents": os.path.join(home, "Documents"),
                    "Downloads": os.path.join(home, "Downloads"),
                    "Music": os.path.join(home, "Music"),
                    "Pictures": os.path.join(home, "Pictures"),
                    "Videos": os.path.join(home, "Videos"),
                }
            else:
                # Linux standard directories
                dirs = {
                    "Desktop": os.path.join(home, "Desktop"),
                    "Documents": os.path.join(home, "Documents"),
                    "Downloads": os.path.join(home, "Downloads"),
                    "Music": os.path.join(home, "Music"),
                    "Pictures": os.path.join(home, "Pictures"),
                    "Videos": os.path.join(home, "Videos"),
                }
            for name, path in dirs.items():
                if os.path.exists(path):
                    standard_dirs.append({"name": name, "path": path})
            logging.info("Standard directories listed successfully.")
            return standard_dirs
        except Exception as e:
            logging.error(f"Failed to list standard directories: {e}")
            return []

    def snapshot_filesystem(self):
        """
        Creates a snapshot of the standard directories' filesystem context and displays it.
        """
        logging.info("Creating filesystem snapshot.")
        
        self.context_display.setPlainText("Creating snapshot, please wait...")
        self.progress_bar.setValue(0)
        self.disable_all_buttons()

        standard_dirs = self.list_standard_directories()

        self.thread = QThread()
        self.snapshot_worker = SnapshotWorker(standard_dirs)
        self.snapshot_worker.moveToThread(self.thread)

        self.thread.started.connect(self.snapshot_worker.snapshot)
        self.snapshot_worker.snapshot_done.connect(self.on_snapshot_done)
        self.snapshot_worker.progress.connect(self.update_progress)
        self.snapshot_worker.error.connect(self.on_snapshot_error)
        self.snapshot_worker.snapshot_done.connect(self.thread.quit)
        self.snapshot_worker.snapshot_done.connect(self.snapshot_worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_snapshot_done(self, snapshot_json):
        self.context_display.setPlainText(snapshot_json)
        self.message_container.setText("Filesystem snapshot created successfully.")
        logging.info("Filesystem snapshot created and displayed.")
        self.enable_buttons()

    def on_snapshot_error(self, error_message):
        self.context_display.setPlainText(f"Error: {error_message}")
        self.message_container.setText("Failed to create filesystem snapshot.")
        logging.error(f"Filesystem snapshot error: {error_message}")
        self.enable_buttons()

    # --- End of New Functions ---
