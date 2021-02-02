import uuid
from typing import List, Dict, Union

from PyQt5.QtCore import (
    QObject,
    QThread,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
    QFile,
    Q_ENUMS,
)
from PyQt5.QtWidgets import qApp

try:
    from icecream import ic
except ImportError:

    def ic(*args, **kwargs):
        pass


_COPY_BLOCK_SIZE = 4096


class CopyError(object):
    NoError = 0
    SourceNotExists = 1
    DestinationExists = 2
    SourceDirectoryOmitted = 3
    SourceFileOmitted = 4
    PathToDestinationNotExists = 5
    CannotCreateDestinationDirectory = 6
    CannotOpenSourceFile = 7
    CannotOpenDestinationFile = 8
    CannotRemoveDestinationFile = 9
    CannotCreateSymLink = 10
    CannotReadSourceFile = 11
    CannotWriteDestinationFile = 12
    CannotRemoveSource = 13
    Cancelled = 14


class _FileCopierWorker(QObject):
    @pyqtProperty(bool)
    def running(self) -> bool:
        return self._running

    @running.setter
    def running(self, running: bool):
        self._running = running

    copy_complete = pyqtSignal(str, arguments=("uid",))
    copy_error = pyqtSignal(str, int, arguments=("uid", "error"))
    copy_progress = pyqtSignal(str, int, int, arguments=("uid", "progress", "total"))
    copy_cancelled = pyqtSignal(str, arguments=("uid",))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._queue: List[Dict[str, str]] = []
        self._running: bool = False
        self._current_uid: Union[str, None] = None
        self._cancel_current: bool = False

    @pyqtSlot(str, str, str)
    def add_to_queue(self, uid: str, source_path: str, dest_path: str):
        self._queue.append(dict(uid=uid, source_path=source_path, dest_path=dest_path))
        if not self.running:
            self._process_queue()

    @pyqtSlot(str)
    def remove_from_queue(self, uid: str):
        if self.running and uid == self._current_uid:
            self._cancel_current = True
        else:
            for index, entry in enumerate(self._queue):
                if entry["uid"] == uid:
                    self._queue.pop(index)
                    break

    @pyqtSlot()
    def clear_queue(self):
        if self.running:
            self._cancel_current = True
        self._queue.clear()

    def _process_queue(self):
        if not len(self._queue):
            self.running = False
            return
        self.running = True

        next_copy = self._queue.pop(0)
        self._copy_file(**next_copy)

        self._process_queue()

    def _copy_file(self, uid: str = "", source_path: str = "", dest_path: str = ""):
        self._current_uid = uid

        source_file = QFile(source_path)
        dest_file = QFile(dest_path)

        if not source_file.open(QFile.ReadOnly):
            self.copy_error.emit(uid, FileCopier.CannotOpenSourceFile)
            return

        if not dest_file.open(QFile.WriteOnly):
            self.copy_error.emit(uid, FileCopier.CannotOpenDestinationFile)
            return

        progress: int = 0
        total: int = source_file.size()
        error: int = FileCopier.NoError
        while True:
            if self._cancel_current:
                self._cancel_current = False
                self.copy_cancelled.emit(uid)
                break

            data: Union[bytes, int] = source_file.read(_COPY_BLOCK_SIZE)
            if isinstance(data, int):
                assert data == -1
                error = FileCopier.CannotReadSourceFile
                break

            data_len = len(data)
            if data_len == 0:
                self.copy_progress.emit(uid, progress, total)
                break

            if data_len != dest_file.write(data):
                error = FileCopier.CannotWriteDestinationFile
                break

            progress += data_len
            self.copy_progress.emit(uid, progress, total)

            qApp.processEvents()

        source_file.close()
        dest_file.close()
        if error != FileCopier.NoError:
            dest_file.remove()
            self.copy_error.emit(uid, error)
        else:
            dest_file.setPermissions(source_file.permissions())
            self.copy_complete.emit(uid)


class FileCopier(QObject, CopyError):
    Q_ENUMS(CopyError)

    _add_to_queue = pyqtSignal(
        str, str, str, arguments=("uid", "source_path", "dest_path")
    )
    _remove_from_queue = pyqtSignal(str, arguments=("uid",))
    _clear_queue = pyqtSignal()

    copy_complete = pyqtSignal(str, arguments=("uid",))
    copy_error = pyqtSignal(str, int, arguments=("uid", "error"))
    copy_progress = pyqtSignal(str, int, int, arguments=("uid", "progress", "total"))
    copy_cancelled = pyqtSignal(str, arguments=("uid",))

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self._thread = QThread()
        self._worker = _FileCopierWorker(
            copy_complete=self.copy_complete,
            copy_error=self.copy_error,
            copy_progress=self.copy_progress,
            copy_cancelled=self.copy_cancelled,
        )
        self._add_to_queue.connect(self._worker.add_to_queue)
        self._remove_from_queue.connect(self._worker.remove_from_queue)
        self._clear_queue.connect(self._worker.clear_queue)
        self._worker.moveToThread(self._thread)
        self._thread.start()

    @staticmethod
    def new_uid():
        return str(uuid.uuid4())

    def copy_file(self, source_path: str, dest_path: str) -> str:
        uid = FileCopier.new_uid()
        self._add_to_queue.emit(uid, source_path, dest_path)
        return uid

    def copy_files(self, source_path_list: List[str], dest_path: str) -> List[str]:
        uid_list = []
        for source_path in source_path_list:
            uid_list.append(self.copy_file(source_path, dest_path))
        return uid_list
