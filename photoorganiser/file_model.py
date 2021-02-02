from typing import Any

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt


class FileModel(QAbstractTableModel):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._data = []
        self._headers = ("File Name", "Source Path", "Destination Path")

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def set_file_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()
