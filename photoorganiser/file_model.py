from typing import Any, List
from recordtype import recordtype

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QObject


FileModelRecord = recordtype(
    "FileModelRecord", ["file_name", "full_path", "dest_path", ("copy", True)]
)


class FileModel(QAbstractTableModel):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._data: List[FileModelRecord] = []
        self._headers = ("File Name", "Source Path", "Destination Path")

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        column = index.column()
        data = self._data[index.row()]
        if role == Qt.DisplayRole:
            if column == 0:
                return data.file_name
            elif column == 1:
                return data.full_path
            elif column == 2:
                return data.dest_path
        if role == Qt.CheckStateRole and column == 0:
            return Qt.Checked if data.copy else Qt.Unchecked
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        if index.column() == 0:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if index.column() == 0 and role == Qt.CheckStateRole:
            self._data[index.row()].copy = value == Qt.Checked
            self.dataChanged.emit(index, index)
            return True
        return super().setData(index, value, role)

    def set_file_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()
