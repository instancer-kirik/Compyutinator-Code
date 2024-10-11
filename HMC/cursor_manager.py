from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QApplication
from typing import List, Dict, Tuple
import re
import os
from bisect import insort
from collections import deque
from typing import Set

class Cursor:
    def __init__(self, line: int, index: int, anchor_line: int = None, anchor_index: int = None):
        self.line = line
        self.index = index
        self.anchor_line = anchor_line if anchor_line is not None else line
        self.anchor_index = anchor_index if anchor_index is not None else index

    def has_selection(self) -> bool:
        return (self.line, self.index) != (self.anchor_line, self.anchor_index)

    def get_selection_range(self) -> Tuple[int, int, int, int]:
        if self.has_selection():
            if (self.line, self.index) < (self.anchor_line, self.anchor_index):
                return self.line, self.index, self.anchor_line, self.anchor_index
            else:
                return self.anchor_line, self.anchor_index, self.line, self.index
        return self.line, self.index, self.line, self.index
    
    def get_position(self) -> Tuple[int, int]:
        return self.line, self.index
class CursorManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.transparent_cursor = QCursor(QPixmap(1, 1))
        self.transparent_cursor.pixmap().fill(Qt.GlobalColor.transparent)
        self.default_cursor = QCursor()

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

    def search_references(self, search_term: str) -> Dict[str, List[Dict[str, int]]]:
        results = {}
        results.update(self.search_vault_index(search_term))
        results.update(self.search_project_index(search_term))
        results.update(self.search_lsp_references(search_term))
        return results

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

class EditorCursorManager:
    def __init__(self, editor):
        self.editor = editor
        self.cursors: List[Cursor] = []
        self.active_cursor_index = 0
        self.cursors_by_line = {}
        self.undo_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)

    def add_cursor(self, line: int, index: int, anchor_line: int = None, anchor_index: int = None):
        cursor = Cursor(line, index, anchor_line, anchor_index)
        self.cursors.append(cursor)
        if line not in self.cursors_by_line:
            self.cursors_by_line[line] = []
        insort(self.cursors_by_line[line], cursor, key=lambda c: c.index)

    def remove_cursor(self, index: int):
        if 0 <= index < len(self.cursors):
            cursor = self.cursors[index]
            del self.cursors[index]
            self.cursors_by_line[cursor.line].remove(cursor)
            if not self.cursors_by_line[cursor.line]:
                del self.cursors_by_line[cursor.line]

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

    def synchronize_cursors(self):
        for cursor in self.cursors:
            # Ensure cursor position is valid
            cursor.line = min(cursor.line, self.editor.lines() - 1)
            cursor.index = min(cursor.index, len(self.editor.text(cursor.line)))
            cursor.anchor_line = min(cursor.anchor_line, self.editor.lines() - 1)
            cursor.anchor_index = min(cursor.anchor_index, len(self.editor.text(cursor.anchor_line)))

    def apply_edit_to_all_cursors(self, edit_function):
        for cursor in self.cursors:
            edit_function(cursor)
        self.synchronize_cursors()

    def move_cursors(self, direction: str, amount: int = 1, move_anchor: bool = False):
        for cursor in self.cursors:
            if direction == 'left':
                cursor.index = max(0, cursor.index - amount)
            elif direction == 'right':
                cursor.index = min(len(self.editor.text(cursor.line)), cursor.index + amount)
            elif direction == 'up':
                if cursor.line > 0:
                    cursor.line -= 1
                    cursor.index = min(cursor.index, len(self.editor.text(cursor.line)))
            elif direction == 'down':
                if cursor.line < self.editor.lines() - 1:
                    cursor.line += 1
                    cursor.index = min(cursor.index, len(self.editor.text(cursor.line)))
            
            if not move_anchor:
                cursor.anchor_line, cursor.anchor_index = cursor.line, cursor.index
        self.synchronize_cursors()

    def insert_text(self, text: str):
        def insert_at_cursor(cursor: Cursor):
            if cursor.has_selection():
                self.editor.setSelection(cursor.anchor_line, cursor.anchor_index, cursor.line, cursor.index)
                self.editor.removeSelectedText()
            self.editor.insertAt(text, cursor.line, cursor.index)
            cursor.index += len(text)
            cursor.anchor_line, cursor.anchor_index = cursor.line, cursor.index
        self.apply_edit_to_all_cursors(insert_at_cursor)
        self.save_state()

    def add_cursors_from_search(self, search_results: Dict[str, List[Dict[str, int]]]):
        current_file = self.editor.file_path
        if current_file in search_results:
            for location in search_results[current_file]:
                line = location['line'] - 1
                column = location['column']
                # Check if there's already a cursor at this position
                if not any(c.line == line and c.index == column for c in self.cursors):
                    self.add_cursor(line, column)
        self.synchronize_cursors()

    def get_cursor_positions(self) -> List[Tuple[int, int, int, int]]:
        return [cursor.get_selection_range() for cursor in self.cursors]

    def get_cursor_lines(self) -> Set[int]:
        return set(cursor.line for cursor in self.cursors)

    def save_state(self):
        state = [(c.line, c.index, c.anchor_line, c.anchor_index) for c in self.cursors]
        self.undo_stack.append(state)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append([(c.line, c.index, c.anchor_line, c.anchor_index) for c in self.cursors])
            state = self.undo_stack.pop()
            self.cursors = [Cursor(*c) for c in state]
            self.synchronize_cursors()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append([(c.line, c.index, c.anchor_line, c.anchor_index) for c in self.cursors])
            state = self.redo_stack.pop()
            self.cursors = [Cursor(*c) for c in state]
            self.synchronize_cursors()

    def expand_selection_to_word(self):
        def expand_cursor(cursor):
            line = self.editor.text(cursor.line)
            start = end = cursor.index
            while start > 0 and line[start-1].isalnum():
                start -= 1
            while end < len(line) and line[end].isalnum():
                end += 1
            cursor.index = end
            cursor.anchor_index = start
        self.apply_edit_to_all_cursors(expand_cursor)

    def expand_selection_to_line(self):
        def expand_cursor(cursor):
            cursor.index = len(self.editor.text(cursor.line))
            cursor.anchor_index = 0
        self.apply_edit_to_all_cursors(expand_cursor)

    def add_cursor_above(self):
        if self.cursors:
            top_cursor = min(self.cursors, key=lambda c: c.line)
            if top_cursor.line > 0:
                new_line = top_cursor.line - 1
                new_index = min(top_cursor.index, len(self.editor.text(new_line)))
                self.add_cursor(new_line, new_index)

    def add_cursor_below(self):
        if self.cursors:
            bottom_cursor = max(self.cursors, key=lambda c: c.line)
            if bottom_cursor.line < self.editor.lines() - 1:
                new_line = bottom_cursor.line + 1
                new_index = min(bottom_cursor.index, len(self.editor.text(new_line)))
                self.add_cursor(new_line, new_index)