from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex
class ObjectTreeModel(QAbstractItemModel):
    def __init__(self, data):
        super().__init__()
        self._root = self._create_tree(data)

    def _create_tree(self, obj, parent=None):
        item = TreeItem(obj, parent)
        if isinstance(obj, dict):
            for key, value in obj.items():
                child = self._create_tree(value, item)
                child.name = str(key)
                item.children.append(child)
        elif isinstance(obj, (list, tuple)):
            for i, value in enumerate(obj):
                child = self._create_tree(value, item)
                child.name = f"[{i}]"
                item.children.append(child)
        elif hasattr(obj, '__dict__'):
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):  # Skip private attributes
                    child = self._create_tree(value, item)
                    child.name = key
                    item.children.append(child)
        return item

    def rowCount(self, parent):
        if parent.isValid():
            return len(parent.internalPointer().children)
        return len(self._root.children)

    def columnCount(self, parent):
        return 2  # Name and Value columns

    def data(self, index, role):
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return item.name
            elif index.column() == 1:
                return str(item.obj)
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return ["Name", "Value"][section]
        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self._root
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.children[row]
        return self.createIndex(row, column, child_item)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent
        if parent_item == self._root:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

class TreeItem:
    def __init__(self, obj, parent=None):
        self.name = type(obj).__name__
        self.obj = obj
        self.parent = parent
        self.children = []

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0
