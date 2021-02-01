from photoorganiser.filecopier import FileCopier

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QWidget
    from sys import argv, exit

    f = FileCopier()

    a = QApplication(argv)
    w = QWidget()
    w.show()
    exit(a.exec())
