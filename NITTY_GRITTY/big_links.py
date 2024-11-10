import os
import shutil
import logging
import stat
import json
import psutil  # For mount points

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QInputDialog, QProgressBar, QFileDialog, QMessageBox, 
    QTreeView, QStyle, QStyledItemDelegate, QAbstractItemView, QTextEdit, QScrollArea, 
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider, QMenu, QDialog, QGroupBox,
    QSplitter
)
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex, QObject, QThread
from PyQt6.QtGui import QFileSystemModel, QIcon, QPainter, QColor, QBrush, QFont
from NITTY_GRITTY.ThreadTrackers import SafeQThread
from GUX.file_explorer import FileExplorerWidget

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
    def paint(self, painter, option, index):
        try:
            model = index.model()
            if not model or not isinstance(model, QFileSystemModel):
                return super().paint(painter, option, index)
                
            # Get file path using proper method
            file_path = model.filePath(index) if hasattr(model, 'filePath') else str(index.data())
            
            if not file_path:
                return super().paint(painter, option, index)
                
            # Draw background
            painter.save()
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            
            # Get file permissions and type
            is_readable = os.access(file_path, os.R_OK)
            is_writable = os.access(file_path, os.W_OK)
            is_symlink = os.path.islink(file_path)
            
            # Calculate text color and icons
            text_color = QColor("#000000")
            if is_symlink:
                text_color = QColor("#0066CC")  # Blue for symlinks
            
            # Draw text with proper color
            painter.setPen(text_color)
            text_rect = option.rect.adjusted(24, 0, -4, 0)  # Leave space for icons
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, index.data())
            
            # Draw permission icons
            icon_rect = option.rect.adjusted(4, 4, -4, -4)
            if is_readable:
                painter.drawText(icon_rect, Qt.AlignmentFlag.AlignLeft, "✓")
            if is_writable:
                painter.drawText(icon_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignLeft, "💾")
            if is_symlink:
                painter.drawText(icon_rect.adjusted(24, 0, 0, 0), Qt.AlignmentFlag.AlignLeft, "🔗")
                
            painter.restore()
            
        except Exception as e:
            logging.error(f"Error in PermissionDelegate paint: {e}")
            super().paint(painter, option, index)

class SymbolicLinkerWidget(QWidget):
    def __init__(self, parent=None, cccore=None):
        super().__init__(parent)
        self.cccore = cccore
        self.source_path = None
        self.target_path = None
        self.bookmarks = []
        self.setup_ui()
        self.load_bookmarks()

    def setup_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar = QHBoxLayout()
        self.create_symlink_button = self.create_tool_button("Create Symlink", self.create_symbolic_link)
        self.rollback_button = self.create_tool_button("Rollback", self.rollback_operation)
        self.remove_symlink_button = self.create_tool_button("Remove Link", self.remove_symlink)
        self.snapshot_button = self.create_tool_button("Snapshot", self.snapshot_filesystem)
        
        toolbar.addWidget(self.create_symlink_button)
        toolbar.addWidget(self.rollback_button)
        toolbar.addWidget(self.remove_symlink_button)
        toolbar.addWidget(self.snapshot_button)
        main_layout.addLayout(toolbar)
        
        # Create search bar
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search files...")
        self.search_box.textChanged.connect(self.filter_view)
        search_layout.addWidget(self.search_box)
        main_layout.addLayout(search_layout)
        
        # Create splitter for explorers
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Source explorer
        self.source_explorer = FileExplorerWidget(self, self.cccore)
        self.source_explorer.file_selected.connect(self.set_source_path)
        source_group = QGroupBox("Source")
        source_layout = QVBoxLayout()
        source_layout.addWidget(self.source_explorer)
        source_group.setLayout(source_layout)
        
        # Target explorer
        self.target_explorer = FileExplorerWidget(self, self.cccore)
        self.target_explorer.file_selected.connect(self.set_target_path)
        target_group = QGroupBox("Target")
        target_layout = QVBoxLayout()
        target_layout.addWidget(self.target_explorer)
        target_group.setLayout(target_layout)
        
        splitter.addWidget(source_group)
        splitter.addWidget(target_group)
        main_layout.addWidget(splitter)
        
        # Add mount points list
        self.mount_points_label = QLabel("Mount Points:")
        main_layout.addWidget(self.mount_points_label)
        self.mount_points_text = QTextEdit()
        self.mount_points_text.setMaximumHeight(60)
        self.mount_points_text.setReadOnly(True)
        main_layout.addWidget(self.mount_points_text)
        self.update_mount_points()
        
        # Path display
        self.path_display = QTextEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setMaximumHeight(60)
        main_layout.addWidget(self.path_display)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Message container
        self.message_container = QLabel()
        self.message_container.setWordWrap(True)
        main_layout.addWidget(self.message_container)
        
        # Context display
        self.context_display = QTextEdit()
        self.context_display.setReadOnly(True)
        self.context_display.setVisible(False)
        main_layout.addWidget(self.context_display)
        
        # Initialize button states
        self.update_button_states()

    def create_tool_button(self, text, slot):
        """Create a toolbar button"""
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        btn.setEnabled(False)  # Initially disabled
        return btn

    def update_mount_points(self):
        """Update the mount points display"""
        mount_points = []
        for partition in psutil.disk_partitions():
            mount_points.append(f"{partition.mountpoint} ({partition.device})")
        self.mount_points_text.setText("\n".join(mount_points))

    def create_symbolic_link(self):
        """Create the symbolic link"""
        try:
            if not self.source_path or not self.target_path:
                return
                
            if os.path.exists(self.target_path):
                os.remove(self.target_path)
                
            os.symlink(self.source_path, self.target_path)
            self.message_container.setText("Symbolic link created successfully!")
            
        except Exception as e:
            self.message_container.setText(f"Failed to create symbolic link: {str(e)}")
            logging.error(f"Failed to create symbolic link: {e}")

    def rollback_operation(self):
        """Rollback the last operation"""
        # Implement rollback logic
        pass

    def remove_symlink(self):
        """Remove the symbolic link"""
        if self.source_path and os.path.islink(self.source_path):
            try:
                os.unlink(self.source_path)
                self.message_container.setText("Symlink removed successfully.")
                self.remove_symlink_button.setEnabled(False)
                self.source_path = None
                logging.info("Removed Symlink")
            except OSError as e:
                self.message_container.setText(f"Failed to remove symlink: {e}")
                logging.error(f"Failed to remove symlink: {e}")

    def filter_view(self, text):
        """Filter both file explorers"""
        self.source_explorer.set_filter(text)
        self.target_explorer.set_filter(text)

    def snapshot_filesystem(self):
        """Create filesystem snapshot"""
        # Implement snapshot logic
        pass

    def update_button_states(self):
        """Update button enabled states"""
        has_paths = bool(self.source_path and self.target_path)
        self.create_symlink_button.setEnabled(has_paths)
        self.rollback_button.setEnabled(False)  # Enable only after operation
        self.remove_symlink_button.setEnabled(bool(self.source_path and os.path.islink(self.source_path)))
        self.snapshot_button.setEnabled(True)  # Always enabled

    
    def set_source_path(self, path):
        """Set source path and update UI"""
        self.source_path = path
        self.update_path_display()
        self.update_button_states()

    def set_target_path(self, path):
        """Set target path and update UI"""
        self.target_path = path
        self.update_path_display()
        self.update_button_states()

    def update_path_display(self):
        """Update the path display text"""
        text = f"Source: {self.source_path or 'None'}\n"
        text += f"Target: {self.target_path or 'None'}"
        self.path_display.setText(text)

    def apply_theme(self):
        """Apply theme colors to the widget"""
        if not hasattr(self.cccore, 'theme_manager'):
            return
            
        theme = self.cccore.theme_manager.current_theme
        colors = theme.get('colors', {})
        
        stylesheet = f"""
            QWidget {{
                background-color: {colors.get('backgroundColor', '#2E3440')};
                color: {colors.get('textColor', '#D8DEE9')};
            }}
            
            QTreeView {{
                background-color: {colors.get('sidebarBackground', '#2E3440')};
                color: {colors.get('sidebarText', '#D8DEE9')};
                border: 1px solid {colors.get('sidebarHighlight', '#3B4252')};
            }}
            
            QTreeView::item:hover {{
                background-color: {colors.get('sidebarHover', '#434C5E')};
            }}
            
            QTreeView::item:selected {{
                background-color: {colors.get('sidebarHighlight', '#3B4252')};
            }}
            
            QTextEdit, QLineEdit {{
                background-color: {colors.get('inputBackground', '#3B4252')};
                color: {colors.get('inputText', '#D8DEE9')};
                border: 1px solid {colors.get('inputBorder', '#434C5E')};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QPushButton {{
                background-color: {colors.get('buttonBackground', '#5E81AC')};
                color: {colors.get('buttonText', '#ECEFF4')};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }}
            
            QPushButton:hover {{
                background-color: {colors.get('buttonHover', '#81A1C1')};
            }}
            
            QPushButton:disabled {{
                background-color: {colors.get('buttonDisabled', '#4C566A')};
                color: {colors.get('buttonDisabledText', '#D8DEE9')};
            }}
            
            QComboBox {{
                background-color: {colors.get('inputBackground', '#3B4252')};
                color: {colors.get('inputText', '#D8DEE9')};
                border: 1px solid {colors.get('inputBorder', '#434C5E')};
                border-radius: 4px;
                padding: 4px;
                min-width: 100px;
            }}
            
            QComboBox::drop-down {{
                border: none;
                background-color: {colors.get('buttonBackground', '#5E81AC')};
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: url({theme.get('icons', {}).get('comboBoxArrow', 'path/to/default/arrow.png')});
            }}
            
            QLabel {{
                color: {colors.get('textColor', '#D8DEE9')};
                font-weight: bold;
            }}
        """
        
        self.setStyleSheet(stylesheet)
        
        # Apply theme to source and target explorers
        if hasattr(self, 'source_explorer'):
            self.source_explorer.apply_theme()
        if hasattr(self, 'target_explorer'):
            self.target_explorer.apply_theme()

    def on_view_mode_changed(self, mode):
        """Handle view mode changes"""
        if mode == "List View":
            # Switch to list view
            pass
        else:
            # Switch to tree view
            pass

    def compare_directories(self):
        """Compare source and target directories for differences"""
        if self.source_path and self.target_path:
            diff = self.get_directory_diff(self.source_path, self.target_path)
            self.show_diff_dialog(diff)

    def batch_rename(self):
        """Open batch rename dialog"""
        if self.source_path:
            self.show_batch_rename_dialog(self.source_path)

    def analyze_sizes(self):
        """Show directory size analysis"""
        if self.source_path:
            self.show_size_analysis(self.source_path)

    def add_bookmark(self):
        """Add current directory to bookmarks"""
        if self.source_path:
            self.save_bookmark(self.source_path)
            self.update_bookmarks_menu()

    def show_diff_dialog(self, diff):
        """Show directory differences in a dialog"""
        dialog = QDialog(self)
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(json.dumps(diff, indent=2))
        layout.addWidget(text_edit)
        dialog.setLayout(layout)
        dialog.exec()

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
        self.create_symlink_button.setEnabled(False)
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

    def load_bookmarks(self):
        """Load bookmarks from settings"""
        if hasattr(self.cccore, 'settings_manager'):
            self.bookmarks = self.cccore.settings_manager.get_value('symbolic_linker_bookmarks', [])
        else:
            self.bookmarks = []

    def save_bookmarks(self):
        """Save bookmarks to settings"""
        if hasattr(self.cccore, 'settings_manager'):
            self.cccore.settings_manager.set_value('symbolic_linker_bookmarks', self.bookmarks)

    # --- End of New Functions ---
