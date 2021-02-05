from PyQt5.QtWidgets import QDialog


class ProgressDialog(QDialog):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
