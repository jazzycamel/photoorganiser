from collections import OrderedDict
from typing import Any, List

from PyQt5.QtCore import (
    QAbstractListModel,
    QModelIndex,
    Qt,
    QItemSelectionModel,
    QItemSelection,
)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListView

from photoorganiser.consts import RAW_FILE_EXTENSIONS


class _FormatModel(QAbstractListModel):
    FORMAT_ROLE = Qt.UserRole + 1

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._data = OrderedDict({"All Image Files": "*"})
        self._data.update(**RAW_FILE_EXTENSIONS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        key = list(self._data.keys())[index.row()]
        if role == Qt.DisplayRole:
            return key
        elif role == _FormatModel.FORMAT_ROLE:
            return self._data[key]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)


class FormatList(QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._model = _FormatModel(self)

        l = QVBoxLayout(self)
        self._view = QListView(self)
        self._view.setModel(self._model)
        self._view.setSelectionBehavior(QListView.SelectRows)
        self._view.setSelectionMode(QListView.MultiSelection)
        self._view.selectionModel().select(
            self._model.index(0, 0), QItemSelectionModel.Select
        )
        l.addWidget(self._view)

    def get_selected_formats(self) -> List[str]:
        selected_indexes = self._view.selectedIndexes()

        formats = []
        for index in selected_indexes:
            formats.append(self._model.data(index, role=_FormatModel.FORMAT_ROLE))

        return formats

    def set_selected_formats(self, formats: List[str]):
        self._view.selectionModel().clearSelection()

        scrolled = False
        item_selection = QItemSelection()
        for format in formats:
            matches = self._model.match(
                self._model.index(0, 0), _FormatModel.FORMAT_ROLE, format
            )
            if not len(matches):
                continue
            item_selection.select(matches[0], matches[0])
            if not scrolled:
                self._view.scrollTo(matches[0], QListView.PositionAtTop)
                scrolled = True

        self._view.selectionModel().select(item_selection, QItemSelectionModel.Select)
