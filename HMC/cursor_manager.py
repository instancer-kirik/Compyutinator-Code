from PyQt6.QtGui import QCursor, QPixmap, QTextCursor
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QApplication
from typing import List, Dict
import re
import os
class Cursor:
    def __init__(self, position: QPoint, text_cursor: QTextCursor = None):
        self.position = position
        self.text_cursor = text_cursor

class CursorManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.transparent_cursor = QCursor(QPixmap(1, 1))
        self.transparent_cursor.pixmap().fill(Qt.GlobalColor.transparent)
        self.default_cursor = QCursor()
        self.cursors: List[Cursor] = []
        self.active_cursor_index = 0

    def set_transparent_cursor(self):
        QApplication.setOverrideCursor(self.transparent_cursor)

    def restore_default_cursor(self):
        QApplication.restoreOverrideCursor()

    def get_current_cursor_pos(self):
        return QCursor.pos()

    def set_cursor_pos(self, pos: QPoint):
        QCursor.setPos(pos)

    def move_cursor_relative(self, dx: int, dy: int):
        current_pos = self.get_current_cursor_pos()
        new_pos = current_pos + QPoint(dx, dy)
        self.set_cursor_pos(new_pos)

    def add_cursor(self, position: QPoint, text_cursor: QTextCursor = None):
        if isinstance(position, QTextCursor):
            text_cursor = position
            position = text_cursor.position()
        self.cursors.append(Cursor(position, text_cursor))

    def remove_cursor(self, index: int):
        if 0 <= index < len(self.cursors):
            del self.cursors[index]

    def clear_cursors(self):
        self.cursors.clear()
        self.active_cursor_index = 0

    def switch_active_cursor(self, index: int):
        if 0 <= index < len(self.cursors):
            self.active_cursor_index = index

    def get_active_cursor(self) -> Cursor:
        if self.cursors:
            return self.cursors[self.active_cursor_index]
        return None

    def search_references(self, search_term: str) -> Dict[str, List[Dict[str, int]]]:
        results = {}
        
        # Search in vault index
        vault_results = self.search_vault_index(search_term)
        if vault_results:
            results.update(vault_results)

        # Search in project index
        project_results = self.search_project_index(search_term)
        if project_results:
            results.update(project_results)

        # Use LSP for more accurate results if available
        lsp_results = self.search_lsp_references(search_term)
        if lsp_results:
            results.update(lsp_results)

        return results

    def search_vault_index(self, search_term: str) -> Dict[str, List[Dict[str, int]]]:
        results = {}
        current_vault = self.cccore.vault_manager.get_current_vault()
        if current_vault and current_vault.index:
            for file_info in current_vault.index['files']:
                file_path = file_info['path']
                with open(file_path, 'r') as f:
                    content = f.read()
                    matches = list(re.finditer(re.escape(search_term), content))
                    if matches:
                        results[file_path] = [{'line': content.count('\n', 0, m.start()) + 1, 'column': m.start() - content.rfind('\n', 0, m.start())} for m in matches]
        return results

    def search_project_index(self, search_term: str) -> Dict[str, List[Dict[str, int]]]:
        results = {}
        current_project = self.cccore.project_manager.get_current_project()
        if current_project:
            project_path = self.cccore.project_manager.get_project_path(current_project)
            for root, _, files in os.walk(project_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                        matches = list(re.finditer(re.escape(search_term), content))
                        if matches:
                            results[file_path] = [{'line': content.count('\n', 0, m.start()) + 1, 'column': m.start() - content.rfind('\n', 0, m.start())} for m in matches]
        return results

    def search_lsp_references(self, search_term: str) -> Dict[str, List[Dict[str, int]]]:
        results = {}
        if hasattr(self.cccore, 'lsp_manager'):
            lsp_results = self.cccore.lsp_manager.find_references(search_term)
            for result in lsp_results:
                file_path = result['uri']
                if file_path not in results:
                    results[file_path] = []
                results[file_path].append({'line': result['range']['start']['line'], 'column': result['range']['start']['character']})
        return results

    def add_cursors_from_search(self, search_results: Dict[str, List[Dict[str, int]]]):
        for file_path, locations in search_results.items():
            editor = self.cccore.editor_manager.open_file(file_path)
            if editor:
                for location in locations:
                    text_cursor = editor.text_edit.textCursor()
                    text_cursor.setPosition(editor.text_edit.document().findBlockByLineNumber(location['line'] - 1).position() + location['column'])
                    self.add_cursor(editor.text_edit.cursorRect(text_cursor).center(), text_cursor)

    def synchronize_cursors(self):
        for cursor in self.cursors:
            if cursor.text_cursor:
                cursor.position = cursor.text_cursor.position()

    def apply_edit_to_all_cursors(self, edit_function):
        for cursor in self.cursors:
            if cursor.text_cursor:
                edit_function(cursor.text_cursor)
        self.synchronize_cursors()