import os
import os.path as osp
import re
from datetime import datetime
from typing import List

import exifread
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QMainWindow,
    QHBoxLayout,
    QFileDialog,
    QFormLayout,
    QComboBox,
    QTableView,
)

from photoorganiser.file_copier import FileCopier, _FileCopierWorker
from photoorganiser.file_model import FileModel, FileModelRecord

try:
    from icecream import ic
except ImportError:

    def ic(*args, **kwargs):
        pass


class PhotoOrganiser(QMainWindow):
    def __init__(self):
        super().__init__()

        self._photo_organiser_widget = PhotoOrganiserWidget(self)
        self.setCentralWidget(self._photo_organiser_widget)


class PhotoOrganiserWidget(QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._file_copier = FileCopier(
            self,
            copy_complete=self.copy_complete,
            copy_error=self.copy_error,
            copy_progress=self.copy_progress,
        )

        l = QVBoxLayout(self)

        source_config_layout = QFormLayout()

        source_path_layout = QHBoxLayout()
        self._source_path_le = QLineEdit(self)
        source_path_layout.addWidget(self._source_path_le)
        source_path_layout.addWidget(
            QPushButton("Browse...", self, clicked=self._browse_for_source_path)
        )
        source_config_layout.addRow("Source:", source_path_layout)

        self._source_file_type_cb = QComboBox(self)
        self._source_file_type_cb.addItems(["All Image Files", "Nikon *.NEF"])
        source_config_layout.addRow("File Type:", self._source_file_type_cb)

        source_config_layout.addRow(
            "", QPushButton("Find files...", self, clicked=self._find_files)
        )

        l.addLayout(source_config_layout)

        self._file_model = FileModel(self)
        table_view = QTableView(self)
        table_view.horizontalHeader().setStretchLastSection(True)
        table_view.setSelectionBehavior(QTableView.SelectRows)
        table_view.setModel(self._file_model)
        l.addWidget(table_view)

        dest_config_layout = QFormLayout()

        dest_path_layout = QHBoxLayout()
        self._dest_path_le = QLineEdit(self)
        dest_path_layout.addWidget(self._dest_path_le)
        dest_path_layout.addWidget(
            QPushButton("Browse...", self, clicked=self._browse_for_dest_path)
        )
        dest_config_layout.addRow("Destination:", dest_path_layout)

        l.addLayout(dest_config_layout)

        self._copy_pb = QPushButton("Copy...", clicked=self._start_copy)
        l.addWidget(self._copy_pb)

    @pyqtSlot()
    def _browse_for_source_path(self):
        path = QFileDialog.getExistingDirectory(self, "Source...")
        if path is None:
            return
        self._source_path_le.setText(path)

    @pyqtSlot()
    def _browse_for_dest_path(self):
        path = QFileDialog.getExistingDirectory(self, "Destination...")
        if path is None:
            return
        self._dest_path_le.setText(path)

    @pyqtSlot()
    def _find_files(self):
        source_path = self._source_path_le.text()
        if not osp.exists(source_path) or not osp.isdir(source_path):
            ic("Source is not a directory...")

        source_file_type = self._source_file_type_cb.currentText()
        if source_file_type.startswith("All"):
            pattern = "(jpg|JPG|nef|NEF)"
        else:
            extension = source_file_type.split(".")[1]
            pattern = f"({extension.lower()}|{extension.upper()})"

        path_re = re.compile(f"^.*.{pattern}$")

        self._file_list: List[FileModelRecord] = []
        for root, directory_names, file_names in os.walk(source_path):
            for file_name in file_names:
                if not path_re.match(file_name):
                    continue

                full_path: str = osp.join(root, file_name)
                exif_tags = exifread.process_file(open(full_path, "rb"), details=False)

                date_time_original = exif_tags["EXIF DateTimeOriginal"].values
                date_time_original = datetime.strptime(
                    date_time_original, "%Y:%m:%d %H:%M:%S"
                )
                camera_model: str = exif_tags["Image Model"].values.replace(" ", "_")

                dest_path: str = osp.join(
                    str(date_time_original.year),
                    str(date_time_original.month),
                    str(date_time_original.day),
                    camera_model,
                    file_name,
                )
                self._file_list.append(FileModelRecord(file_name, full_path, dest_path))

        self._file_model.set_file_data(self._file_list)

    @pyqtSlot()
    def _start_copy(self):
        pass

    # source_path = self._file_source_le.text()
    # ic(source_path)
    #
    # dest_path = self._file_dest_le.text()
    # ic(dest_path)
    #
    # self._file_copier.copy_file(source_path, dest_path)

    @pyqtSlot(str)
    def copy_complete(self, uid: str):
        ic(uid)

    @pyqtSlot(str, int)
    def copy_error(self, uid: str, error: int):
        ic(uid, error)

    @pyqtSlot(str, int, int)
    def copy_progress(self, uid: str, progress: int, total: int):
        pass

    # self._progress_bar.setEnabled(True)
    # self._progress_bar.setRange(0, total)
    # self._progress_bar.setValue(progress)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from sys import argv, exit

    a = QApplication(argv)
    a.setApplicationName("PhotoOrganiser")
    a.setApplicationDisplayName(a.applicationName())
    a.setOrganizationName("jazzycamel")
    a.setOrganizationDomain("https://github.com/jazzycamel/photoorganiser")
    a.setApplicationVersion("0.1")

    p = PhotoOrganiser()
    p.show()
    exit(a.exec())
