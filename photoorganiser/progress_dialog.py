from typing import Dict

from PyQt5.QtWidgets import QDialog, QProgressBar, QFormLayout, QLabel, QDialogButtonBox

from photoorganiser.file_model import FileModelRecord

try:
    from icecream import ic
except ImportError:

    def ic(*args, **kwargs):
        pass


class ProgressDialog(QDialog):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._errors = 0

        l = QFormLayout(self)

        self._file_list_progress = QProgressBar(self)
        self._file_list_progress.setFormat("%v/%m")
        l.addRow("Files copied:", self._file_list_progress)

        self._file_copy_progress = QProgressBar(self)
        l.addRow("Current File Progress:", self._file_copy_progress)

        self._current_file_label = QLabel(self)
        l.addRow("", self._current_file_label)

        self._error_count_label = QLabel("0", self)
        l.addRow("Errors:", self._error_count_label)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok, self)
        self._button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self._button_box.accepted.connect(self.accept)
        l.addWidget(self._button_box)

        self.setModal(True)

    def set_file_dict(self, file_dict: Dict[str, str]):
        self._file_dict = file_dict
        self._file_list_progress.setRange(0, len(file_dict))
        self._file_list_progress.setValue(0)
        self._errors = 0

    def set_file_progress(self, uid: str, progress: int, total: int):
        current_file: FileModelRecord = self._file_dict[uid]
        self._current_file_label.setText(current_file.file_name)
        self._file_copy_progress.setRange(0, total)
        self._file_copy_progress.setValue(progress)

    def file_copy_error(self, uid: str):
        self._file_dict.pop(uid)
        self._file_list_progress.setRange(0, len(self._file_dict))
        self._errors += 1
        self._error_count_label.setText(f"{self._errors}")

    def file_copy_finished(self):
        self._file_list_progress.setValue(self._file_list_progress.value() + 1)
        if self._file_list_progress.value() == self._file_list_progress.maximum():
            self._current_file_label.setText("")
            self._button_box.button(QDialogButtonBox.Ok).setEnabled(True)
