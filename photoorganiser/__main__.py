import os
import os.path as osp
import re
from datetime import datetime
from typing import List, Dict

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
    QTableView,
)

from photoorganiser.consts import RAW_FILE_EXTENSIONS
from photoorganiser.file_copier import FileCopier
from photoorganiser.file_model import FileModel, FileModelRecord
from photoorganiser.format_list import FormatList
from photoorganiser.progress_dialog import ProgressDialog
from photoorganiser.settings import Settings

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

        self._progress_dialog = ProgressDialog(self)

        l = QVBoxLayout(self)

        source_config_layout = QFormLayout()

        source_path_layout = QHBoxLayout()
        self._source_path_le = QLineEdit(self)
        source_path_layout.addWidget(self._source_path_le)
        source_path_layout.addWidget(
            QPushButton("Browse...", self, clicked=self._browse_for_source_path)
        )
        source_config_layout.addRow("Source:", source_path_layout)

        self._source_format_list = FormatList(self)
        source_config_layout.addRow("File Type:", self._source_format_list)

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

        with Settings() as s:
            if len(s["dest"]["path"]):
                self._dest_path_le.setText(s["dest"]["path"])
            if len(s["file_type"]["file_type"]):
                self._source_format_list.set_selected_formats(
                    s["file_type"]["file_type"]
                )

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

        with Settings() as s:
            s["dest"]["path"] = path

    @pyqtSlot()
    def _find_files(self):
        source_path = self._source_path_le.text()
        if not osp.exists(source_path) or not osp.isdir(source_path):
            ic("Source is not a directory...")
            return

        formats = self._source_format_list.get_selected_formats()
        with Settings() as s:
            s["file_type"]["file_type"] = formats

        if "*" in formats:
            formats = RAW_FILE_EXTENSIONS.values()

        exts = "|".join([f"{ext.lower()}|{ext.upper()}" for ext in formats])
        path_re = re.compile(f"^.*.({exts})$")

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
        dest_path = self._dest_path_le.text()
        self._copy_pb.setDisabled(True)

        self._copy_dict: Dict[str, str] = {}

        for file_record in self._file_model.file_data():
            if not file_record.copy:
                continue

            uid = self._file_copier.copy_file(
                file_record.full_path, osp.join(dest_path, file_record.dest_path)
            )
            self._copy_dict[uid] = file_record

        self._progress_dialog.set_file_dict(self._copy_dict)
        self._progress_dialog.show()

    @pyqtSlot(str)
    def copy_complete(self, uid: str):
        self._progress_dialog.file_copy_finished()
        self._copy_dict.pop(uid)
        if not len(self._copy_dict):
            self._copy_pb.setEnabled(True)

    @pyqtSlot(str, int)
    def copy_error(self, uid: str, error: int):
        ic(uid, error, self._copy_dict[uid])
        self._progress_dialog.file_copy_error(uid)

    @pyqtSlot(str, int, int)
    def copy_progress(self, uid: str, progress: int, total: int):
        self._progress_dialog.set_file_progress(uid, progress, total)


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
