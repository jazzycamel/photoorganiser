import sys
from typing import List, Union, Dict, Set

from PyQt5.QtCore import (
    QObject,
    pyqtProperty,
    Q_ENUMS,
    pyqtSlot,
    pyqtSignal,
    QThread,
    QMutex,
    QMutexLocker,
    QWaitCondition,
    QCoreApplication,
    QFileInfo,
    QFile,
)

StrList = List[str]
IntList = List[int]


class State(object):
    Idle = 0
    Busy = 1
    WaitingForInteraction = 2


class CopyFlag(object):
    NonInteractive = 0x01
    Force = 0x02
    MakeLinks = 0x04
    FollowLinks = 0x08


class Error(object):
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


class FileCopier(QObject, State, CopyFlag, Error):
    Q_ENUMS(State)
    Q_ENUMS(CopyFlag)
    Q_ENUMS(Error)

    error = pyqtSignal(int, int, bool, arguments=("id", "error", "stopped"))
    stateChanged = pyqtSignal(int, arguments=("state",))
    done = pyqtSignal(bool, arguments=("error",))
    started = pyqtSignal(int, arguments=("id",))
    dataTransferProgress = pyqtSignal(int, int, arguments=("id", "progress"))
    finished = pyqtSignal(int, bool, arguments=("id", "error"))
    cancelled = pyqtSignal()

    # Progress Interval Property
    @pyqtProperty(int)
    def progressInterval(self) -> int:
        return self._interval

    @progressInterval.setter
    def progressInterval(self, interval: int):
        self._interval = interval

    def setProgressInterval(self, interval: int):
        self.progressInterval = interval

    # Auto Reset Property
    @pyqtProperty(bool)
    def autoReset(self) -> bool:
        return self._autoReset

    @autoReset.setter
    def autoReset(self, on: bool):
        self._autoReset = on

    def setAutoReset(self, on: bool):
        self.autoReset = on

    def __init__(self):
        super().__init__()

        self._interval = 0
        self._autoReset = False

    def copy(self, sourceFile: str, destinationPath: str, flags: int = 0) -> int:
        return 0

    def copyFiles(
        self, sourceFiles: StrList, destinationDir: str, flags: int = 0
    ) -> IntList:
        return [0]

    def copyDirectory(
        self, sourceDir: str, destinationDir: str, flags: int = 0
    ) -> IntList:
        return [0]

    def move(self, sourceFile: str, destinationPath: str, flags: int = 0) -> int:
        return 0

    def moveFiles(self, sourceDir: str, destinationDir: str, flags: int = 0) -> IntList:
        return [0]

    def moveDirectory(
        self, sourceDir: str, destinationDir: str, flags: int = 0
    ) -> IntList:
        return [0]

    def pendingRequests(self) -> IntList:
        return [0]

    def sourceFilePath(self, id_: int) -> str:
        return ""

    def destinationFilePath(self, id_: int) -> str:
        return ""

    def isDir(self, id_: int) -> bool:
        return False

    def entryList(self, id_: int) -> IntList:
        return [0]

    def currentId(self) -> int:
        return 0

    def state(self) -> int:
        return State.Idle

    @pyqtSlot()
    def cancelAll(self):
        pass

    @pyqtSlot(int)
    def cancel(self, id_: int):
        pass

    @pyqtSlot()
    def skip(self):
        pass

    @pyqtSlot()
    def skipAll(self):
        pass

    @pyqtSlot()
    def retry(self):
        pass

    @pyqtSlot()
    def overwrite(self):
        pass

    @pyqtSlot()
    def overwriteAll(self):
        pass

    @pyqtSlot()
    def reset(self):
        pass

    @pyqtSlot()
    def resetSkip(self):
        pass

    @pyqtSlot()
    def resetOverwrite(self):
        pass

    @pyqtSlot(int)
    def _copyStarted(self, id_: int):
        pass

    @pyqtSlot(int, bool)
    def _copyFinished(self, id_: int, error: bool):
        pass

    @pyqtSlot()
    def _copyCancelled(self):
        pass

    @pyqtSlot(int, int, bool)
    def _copyError(self, id_: int, error: int, arg3: bool):
        pass

    @pyqtSlot()
    def _progressRequest(self):
        pass


class CopyRequest(object):
    def __init__(self):
        self.move: bool = False
        self.dir: bool = False
        self.childrenQueue: IntList = []
        self.source: str = ""
        self.dest: str = ""
        self.copyFlags: int = 0


class CopyThread(QThread):
    class Request(object):
        def __init__(self, r: CopyRequest = None):
            self.request = r
            self.cancelled = False
            self.overwrite = False
            self.moveError = False

    error = pyqtSignal(int, int, bool, arguments=("id", "error", "stopped"))
    started = pyqtSignal(int, arguments=("id",))
    dataTransferProgress = pyqtSignal(int, int, arguments=("id", "progress"))
    finished = pyqtSignal(int, bool, arguments=("id", "error"))
    cancelled = pyqtSignal()

    def __init__(self, fileCopier: FileCopier):
        super().__init__(QCoreApplication.instance())

        self._copier: FileCopier = fileCopier
        self._requestQueue: Dict[int, CopyThread.Request] = {}
        self._mutex = QMutex()
        self._newCopyCondition = QWaitCondition()
        self._interactionCondition = QWaitCondition()
        self._waitingForInteraction: bool = False
        self._stopRequest: bool = False
        self._skipAllRequest: bool = False
        self._skipAllError: Set[Error] = set()
        self._overwriteAllRequest: bool = False
        self._cancelRequest: bool = False
        self._currentId: int = -1
        self._progressRequest: int = 0
        self._autoReset: bool = True

        self.error.connect(self._copier._copyError)
        self.started.connect(self._copier._copyStarted)
        self.dataTransferProgress.connect(self._copier.dataTransferProgress)
        self.finished.connect(self._copier._copyFinished)
        self.cancelled.connect(self._copier._copyCancelled)
        self._copier.destroyed.connect(self._copierDestroyed)

    def __del__(self):
        if self.isRunning():
            self.wait()

    def emitProgress(self, id_: int, progress: int):
        l = QMutexLocker(self._mutex)
        self.dataTransferProgress.emit(id_, progress)
        self._progressRequest = 0

    def isCancelled(self, id_: int) -> bool:
        l = QMutexLocker(self._mutex)
        if self._cancelRequest:
            return True
        try:
            return self._requestQueue[id_].cancelled
        except KeyError:
            return False

    def isMoveError(self, id_: int) -> bool:
        l = QMutexLocker(self._mutex)
        try:
            return self._requestQueue[id_].moveError
        except KeyError:
            return False

    def setMoveError(self, id_: int, error: bool) -> bool:
        l = QMutexLocker(self._mutex)
        if not len(self._requestQueue):
            return
        self._requestQueue[id_].moveError = error

    def isProgressRequest(self):
        return self._progressRequest != 0

    def handle(self, id_: int):
        if self._cancelRequest:
            return

        self._mutex.lock()
        oldCurrentId = self._currentId
        self._currentId = id_
        self._mutex.unlock()

        self.started.emit(id_)
        done = False
        error = FileCopier.NoError
        while not done:
            self._mutex.lock()
            request = self._requestQueue[id_]
            overwriteAll = self._overwriteAllRequest
            self._mutex.unlock()
            copyRequest = request.request

            n = CopyFileNode(None, id_, copyRequest, self)
            n = CopyDirNode(n)
            n = MoveNode(n)
            n = RenameNode(n)
            n = FollowLinksNode(n)
            n = MakeLinksNode(n)
            n = OverwriteNode(n, request.overwrite or overwriteAll)
            n = SourceExistsNode(n)
            n = CancelledNode(n, request.cancelled)

            done = n.handle()
            error = n.error()
            del n

            if done or copyRequest.copyFlags & FileCopier.NonInteractive:
                done = True
                if error != FileCopier.NoError:
                    self.error.emit(id_, error, False)
            else:
                self._mutex.lock()
                if self._stopRequest or error in self._skipAllError:
                    done = True
                    if not self._stopRequest:
                        self.error.emit(id_, error, False)
                else:
                    self.error.emit(id_, error, True)
                    self._waitingForInteraction = True
                    self._interactionCondition.wait(self._mutex)
                    if self._skipAllRequest:
                        self._skipAllRequest = False
                        self._skipAllError.add(error)
                    self._waitingForInteraction = False
                self._mutex.unlock()

        self.finished.emit(id_, error != FileCopier.NoError)
        self._mutex.lock()
        self._currentId = oldCurrentId
        self._requestQueue.pop(id_)
        self._mutex.unlock()

    def lockCancelChildren(self, id_: int):
        l = QMutexLocker(self._mutex)
        self._cancelChildren(id_)

    def renameChildren(self, id_: int):
        self._mutex.lock()
        request = self._requestQueue[id_].request
        oldCurrentId = self._currentId
        self._currentId = id_
        self._mutex.unlock()
        self.started.emit(id_)

        while len(request.childrenQueue):
            self.renameChildren(request.childrenQueue.pop(-1))

        if not request.dir:
            destinationFileInfo = QFileInfo(request.dest)
            self.emitProgress(id_, destinationFileInfo.size())

        self.finished.emit(id_, False)
        self._mutex.lock()
        self._currentId = oldCurrentId
        self._requestQueue.pop(id_)
        self._mutex.unlock()

    def cancelChildRequests(self, id_: int):
        request = self._requestQueue[id_]
        request.cancelled = True
        for childId in request.request.childrenQueue:
            self.cancelChildRequests(childId)

    def overwriteChildRequests(self, id_: int):
        request = self._requestQueue[id_]
        request.overwrite = True
        for childId in request.request.childrenQueue:
            self.overwriteChildRequests(childId)

    def setAutoReset(self, on: bool):
        l = QMutexLocker(self._mutex)
        self._autoReset = on

    @pyqtSlot()
    def restart(self):
        self.start()
        self._newCopyCondition.wakeOne()

    @pyqtSlot(dict)
    @pyqtSlot(int, CopyRequest)
    def copy(self, id_: Union[int, dict], copyRequest: CopyRequest = None):
        l = QMutexLocker(self._mutex)
        if isinstance(id_, dict):
            requests = id_
        else:
            requests = {id_: copyRequest}

        for request in requests:
            self._requestQueue[id_] = CopyThread.Request(request)

    @pyqtSlot()
    @pyqtSlot(int)
    def cancel(self, id_: int = None):
        l = QMutexLocker(self._mutex)

        if id_:
            self.cancelChildRequests(id_)
            return

        for id_, request in self._requestQueue.items():
            request.cancelled = True
        self._cancelRequest = True

    @pyqtSlot()
    def skip(self):
        l = QMutexLocker(self._mutex)
        if not self._waitingForInteraction:
            return
        self.cancelChildRequests(self._currentId)
        self._interactionCondition.wakeOne()
        self._waitingForInteraction = False

    @pyqtSlot()
    def skipAll(self):
        l = QMutexLocker(self._mutex)
        if not self._waitingForInteraction:
            return
        self.cancelChildRequests(self._currentId)
        self._skipAllRequest = True
        self._interactionCondition.wakeOne()
        self._waitingForInteraction = False

    @pyqtSlot()
    def retry(self):
        l = QMutexLocker(self._mutex)
        if not self._waitingForInteraction:
            return
        self._interactionCondition.wakeOne()
        self._waitingForInteraction = False

    @pyqtSlot()
    def overwrite(self):
        l = QMutexLocker(self._mutex)
        if not self._waitingForInteraction:
            return
        self.overwriteChildRequests(self._currentId)
        self._interactionCondition.wakeOne()
        self._waitingForInteraction = False

    @pyqtSlot()
    def overwriteAll(self):
        l = QMutexLocker(self._mutex)
        if not self._waitingForInteraction:
            return
        self.overwriteChildRequests(self._currentId)
        self._interactionCondition.wakeOne()
        self._waitingForInteraction = False

    @pyqtSlot()
    def resetOverwrite(self):
        l = QMutexLocker(self._mutex)
        self._overwriteAllRequest = True

    @pyqtSlot()
    def resetSkip(self):
        l = QMutexLocker(self._mutex)
        self._skipAllError.clear()

    @pyqtSlot()
    def progress(self):
        self._progressRequest = 1

    def run(self):
        stop = False
        while not stop:
            self._mutex.lock()
            if not len(self._requestQueue):
                if self._stopRequest:
                    self._mutex.unlock()
                    stop = True
                else:
                    self._progressRequest = 0
                    self._cancelRequest = False
                    self._newCopyCondition.wait(self._mutex)
                    if self._autoReset:
                        self._overwriteAllRequest = False
                        self._skipAllError.clear()
                    self._mutex.unlock()
            else:
                if self._cancelRequest:
                    self._requestQueue.clear()
                    self._cancelRequest = False
                    self.cancelled.emit()
                    self._mutex.unlock()
                else:
                    self._mutex.unlock()
                    self.handle(list(self._requestQueue.keys())[0])
        self.deleteLater()

    @pyqtSlot()
    def _copierDestroyed(self):
        l = QMutexLocker(self._mutex)
        self._stopRequest = True
        self._newCopyCondition.wakeOne()
        self._interactionCondition.wakeOne()

    def _cancelChildren(self, id_: int):
        try:
            request = self._requestQueue[id_].request
        except KeyError:
            return

        while len(request.childrenQueue):
            childId = request.childrenQueue.pop(-1)
            self._cancelChildren(childId)
            self._requestQueue.pop(childId)


class ChainNode(object):
    def __init__(self, nextInChain=None):
        self._n: ChainNode = nextInChain
        self._err = FileCopier.NoError

    def __del__(self):
        if self._n:
            del self._n

    def error(self) -> int:
        if self._n:
            return self._n.error()
        return self._err

    def handle(self) -> bool:
        if self._n:
            return self._n.handle()
        return False

    def request(self) -> CopyRequest:
        return self._n.request()

    def thread(self) -> Union[CopyThread, None]:
        if self._n:
            return self._n.thread()
        return None

    def currentId(self) -> int:
        if self._n:
            return self._n.currentId()
        return -1

    def setError(self, error: int):
        if self._n:
            self._n.setError(error)
        else:
            self._err = error


class CancelledNode(ChainNode):
    def __init__(self, nextInChain: ChainNode, cancelled: bool):
        super().__init__(nextInChain)
        self._cancelled = cancelled

    def handle(self) -> bool:
        if not self._cancelled:
            return super().handle()
        request = self.request()
        if request.dir:
            self.thread().lockCancelChildren(self.currentId())
        self.setError(FileCopier.Cancelled)
        return True


class SourceExistsNode(ChainNode):
    def handle(self) -> bool:
        request = self.request()
        sourceFileInfo = QFileInfo(request.source)
        if not sourceFileInfo.exists() and not sourceFileInfo.isSymLink():
            self.setError(FileCopier.SourceNotExists)
            return False
        return super().handle()


class OverwriteNode(ChainNode):
    def __init__(self, nextInChain: ChainNode, overwrite: bool):
        super().__init__(nextInChain)
        self._overwrite = overwrite

    def handle(self) -> bool:
        request = self.request()
        destinationFileInfo = QFileInfo(request.dest)
        overwrite = (
            True if request.copyFlags & FileCopier.NonInteractive else self._overwrite
        )

        if (
            destinationFileInfo.exists() or destinationFileInfo.isSymLink()
        ) and not overwrite:
            self.setError(FileCopier.DestinationExists)
            return False
        return super().handle()


class MakeLinksNode(ChainNode):
    def handle(self) -> bool:
        request = self.request()

        if not request.copyFlags & FileCopier.MakeLinks:
            return super().handle()

        sourceFileInfo = QFileInfo(request.source)
        destinationFileInfo = QFileInfo(request.dest)
        dir = destinationFileInfo.dir()

        if sys.platform == "win32":
            linkName = sourceFileInfo.absoluteFilePath()
        else:
            linkName = dir.relativeFilePath(sourceFileInfo.filePath())

        sourceFile = QFile(linkName)
        if sourceFile.link(request.dest):
            return True

        self.setError(FileCopier.CannotCreateSymLink)
        return False


class FollowLinksNode(ChainNode):
    def handle(self) -> bool:
        request = self.request()
        sourceFileInfo = QFileInfo(request.source)

        if (
            sourceFileInfo.isSymLink()
            and not request.copyFlags & FileCopier.FollowLinks
        ):
            linkFileInfo = QFileInfo(sourceFileInfo.symLinkTarget())
            linkName = linkFileInfo.filePath()

            if sys.platform == "win32":
                linkName = linkFileInfo.absoluteFilePath()
            else:
                if linkFileInfo.isAbsolute():
                    dir = linkFileInfo.dir()
                    linkName = dir.relativeFilePath(linkName)

            linkTarget = QFile(linkName)
            if linkTarget.link(request.dest):
                return True

            self.setError(FileCopier.CannotCreateSymLink)
            return False
        return super().handle()


class RenameNode(ChainNode):
    def handle(self) -> bool:
        request = self.request()
        if request.move:
            sourceFileInfo = QFileInfo(request.source)
            dir = sourceFileInfo.dir()
            if not (request.copyFlags & FileCopier.FollowLinks) or (
                not request.dir and not sourceFileInfo.isSymLink()
            ):
                if dir.rename(sourceFileInfo.fileName(), request.dest):
                    destinationFileInfo = QFileInfo(request.dest)
                    if request.dir:
                        while len(request.childrenQueue):
                            self.thread().renameChildren(request.childrenQueue.pop(-1))
                    else:
                        self.thread().emitProgress(
                            self.currentId(), destinationFileInfo.size()
                        )
                    return True
        return super().handle()


class MoveNode(ChainNode):
    def handle(self) -> bool:
        request = self.request()
        done = True

        if not self.thread().isMoveError(self.currentId()):
            done = super().handle()
        if done and self.error() == FileCopier.NoError and request.move:
            moveError = False
            sourceFileInfo = QFileInfo(request.source)
            sourceDir = sourceFileInfo.dir()
            if sourceFileInfo.isDir() and not sourceFileInfo.isSymLink():
                if not sourceDir.rmdir(sourceFileInfo.fileName()):
                    moveError = True
            elif not sourceDir.remove(sourceFileInfo.fileName()):
                moveError = True

            self.thread().setMoveError(self.currentId(), moveError)
            if moveError:
                self.setError(FileCopier.CannotRemoveSource)
                done = False
        return done


class CopyDirNode(ChainNode):
    def handle(self) -> bool:
        request = self.request()
        if not request.dir:
            return super().handle()

        sourceFileInfo = QFileInfo(request.source)
        if not sourceFileInfo.isDir():
            self.setError(FileCopier.SourceFileOmitted)
            return False

        destinationFileInfo = QFileInfo(request.dest)
        if not destinationFileInfo.exists():
            destDir = destinationFileInfo.dir()
            if not destDir.exists():
                self.setError(FileCopier.PathToDestinationNotExists)
                return False
            elif not destDir.mkdir(destinationFileInfo.fileName()):
                self.setError(FileCopier.CannotCreateDestinationDirectory)
                return False
        elif destinationFileInfo.isSymLink() or destinationFileInfo.isFile():
            self.setError(FileCopier.CannotCreateDestinationDirectory)
            return False

        while len(request.childrenQueue):
            self.thread().handle(request.childrenQueue.pop(-1))

        if self.thread().isCancelled(self.currentId()):
            self.setError(FileCopier.Cancelled)

        return True


class CopyFileNode(ChainNode):
    def __init__(
        self,
        nextInChain: ChainNode,
        currentId: int,
        request: CopyRequest,
        thread: CopyThread,
    ):
        super().__init__(nextInChain)
        self._id = currentId
        self._request = request
        self._thread = thread

    def request(self) -> CopyRequest:
        return self._request

    def thread(self) -> CopyThread:
        return self._thread

    def currentId(self) -> int:
        return self._id

    def handle(self) -> bool:
        request = self.request()

        if request.dir:
            self.setError(FileCopier.SourceDirectoryOmitted)
            return False

        sourceFile = QFile(request.source)
        destFile = QFile(request.dest)

        if not sourceFile.open(QFile.ReadOnly):
            self.setError(FileCopier.CannotOpenSourceFile)
            return False

        if not destFile.open(QFile.WriteOnly):
            done = False
            if request.copyFlags & FileCopier.Force:
                destinationFileInfo = QFileInfo(request.dest)
                dir = destinationFileInfo.dir()
                if not dir.remove(destinationFileInfo.fileName()):
                    self.setError(FileCopier.CannotRemoveDestinationFile)
                elif not destFile.open(QFile.WriteOnly):
                    self.setError(FileCopier.CannotOpenDestinationFile)
                else:
                    done = True
            else:
                self.setError(FileCopier.CannotOpenDestinationFile)

            if not done:
                sourceFile.close()
                return False

        progress = 0
        done = False
        while True:
            if self._thread.isCancelled(self._id):
                self.setError(FileCopier.Cancelled)
                done = True
                break

            block: [bytes, int] = sourceFile.read(4096)

            if isinstance(block, int) or block == -1:
                self.setError(FileCopier.CannotReadSourceFile)
                break

            in_ = len(block)
            if not in_:
                self._thread.emitProgress(self._id, progress)
                break

            if in_ != destFile.write(block):
                self.setError(FileCopier.CannotWriteDestinationFile)
                break

            progress += in_
            if self._thread.isProgressRequest():
                self._thread.emitProgress(self._id, progress)

        destFile.close()
        sourceFile.close()

        if self.error() != FileCopier.NoError:
            destFile.remove()
        else:
            destFile.setPermissions(sourceFile.permissions())
            done = True

        return done
