from PyQt5.QtWidgets import QDialog, QProgressBar, QFormLayout, QLabel

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

        self._error_count_label = QLabel("0", self)
        l.addRow("Errors:", self._error_count_label)

        self.setModal(True)

    def set_file_count(self, count: int):
        ic(count)
        self._errors = 0
        self._file_list_progress.setRange(0, count)
        self._file_list_progress.setValue(0)

    def set_file_progress(self, uid: str, progress: int, total: int):
        self._file_copy_progress.setRange(0, total)
        self._file_copy_progress.setValue(progress)

    def file_copy_error(self):
        self._file_list_progress.setRange(0, self._file_list_progress.maximum() - 1)
        self._errors += 1
        self._error_count_label.setText(f"{self._errors}")

    def file_copy_finished(self):
        ic(self._file_list_progress.value())
        self._file_list_progress.setValue(self._file_list_progress.value() + 1)
