import toml
import os, os.path as osp
from PyQt5.QtCore import QStandardPaths as QSP

from photoorganiser.utils import Singleton

try:
    from icecream import ic
except ImportError:

    def ic(*args, **kwargs):
        pass


class Settings(object, metaclass=Singleton):
    def __init__(self):
        ic("Settings Init")

        config_dir = QSP.standardLocations(QSP.AppConfigLocation)[0]
        self._settings_file_path = osp.join(
            config_dir, "photoorganiser", "photoorganiser.toml"
        )

        if not osp.exists(self._settings_file_path):
            os.makedirs(osp.dirname(self._settings_file_path), exist_ok=True)
            self._config_data = {
                "title": "PhotoOrganiser Settings",
                "file_type": {"file_type": []},
                "dest": {"path": ""},
            }

        else:
            self._config_data = toml.load(self._settings_file_path)

    def flush(self):
        with open(self._settings_file_path, "w") as f:
            toml.dump(self._config_data, f)

    def __enter__(self):
        ic("Settings enter")
        return self._config_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        ic("Settings exit", exc_type, exc_val, exc_tb)
        self.flush()
