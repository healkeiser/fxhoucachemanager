import configparser
import os
from pathlib import Path
from typing import Dict, Union

# Third-party
from hutil.Qt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFormLayout,
)
from hutil.Qt.QtCore import Qt, Signal

# Internal
from fxhoucachemanager import fxenvironment

# Reload modules if in debug mode
if os.getenv("DEBUG_CODE") == "1":
    from importlib import reload

    reload(fxenvironment)


def load_config(
    config_path: Union[
        str, Path
    ] = fxenvironment.FXCACHEMANAGER_USER_CONFIG_PATH
) -> Dict:
    """Load configuration from an `INI` file.

    Args:
        config_path: Path to the configuration file. If the path does not
            exist, the default configuration path will be used.

    Returns:
        dict: Configuration dictionary.
    """

    # Convert to Path object
    config_path = Path(config_path)

    # Use default configuration if the path does not exist
    if not config_path.exists():
        config_path = fxenvironment.FXCACHEMANAGER_DEFAULT_CONFIG_PATH

    config = configparser.ConfigParser()
    config.read(config_path)

    return {
        "version_pattern": config.get("Settings", "version_pattern"),
        "houdini_variable": config.get("Settings", "houdini_variable"),
        "cache_root_path": os.path.expandvars(
            config.get("Settings", "cache_root_path")
        ),
    }


class FXSettingsDialog(QDialog):

    settings_applied = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 300)

        self.config_path = fxenvironment.FXCACHEMANAGER_USER_CONFIG_PATH
        self.default_config_path = (
            fxenvironment.FXCACHEMANAGER_DEFAULT_CONFIG_PATH
        )
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

        self.descriptions = self.parse_descriptions(self.config_path)

        self._init_ui()
        self.load_settings()

    def parse_descriptions(
        self, config_path: Union[str, Path]
    ) -> Dict[str, str]:
        """Parse descriptions from the INI file.

        Args:
            config_path: Path to the configuration file.

        Returns:
            A dictionary where the keys are in the format 'section.key'
                and the values are the descriptions.
        """

        descriptions = {}
        with open(config_path, "r") as file:
            section = None
            description = ""
            for line in file:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    description = ""
                elif line.startswith(";") or line.startswith("#"):
                    description = line[1:].strip()
                elif "=" in line and section:
                    key = line.split("=")[0].strip()
                    descriptions[f"{section}.{key}"] = description
                    description = ""
        return descriptions

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Form layout for settings
        form_layout = QFormLayout()
        self.settings_fields = {}

        for section in self.config.sections():
            for key in self.config[section]:
                prettified_key = key.replace("_", " ").capitalize()
                label = QLabel(prettified_key)
                line_edit = QLineEdit()
                description = self.descriptions.get(f"{section}.{key}", "")
                line_edit.setToolTip(
                    f"<b>{prettified_key}</b><hr>{description}"
                )
                form_layout.addRow(label, line_edit)
                self.settings_fields[prettified_key] = (
                    section,
                    key,
                    line_edit,
                )

        layout.addLayout(form_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(self.apply_button, alignment=Qt.AlignLeft)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_to_default)
        buttons_layout.addWidget(self.reset_button, alignment=Qt.AlignLeft)

        buttons_layout.addStretch()

        self.accept_button = QPushButton("Accept")
        self.accept_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.accept_button, alignment=Qt.AlignRight)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)

        layout.addLayout(buttons_layout)

    def load_settings(self):
        """Load settings from the configuration file."""

        for _, (section, key, line_edit) in self.settings_fields.items():
            line_edit.setText(self.config[section][key])

    def apply_settings(self):
        """Apply settings to the configuration file."""

        for _, (section, key, line_edit) in self.settings_fields.items():
            self.config[section][key] = line_edit.text()

        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)

        self.settings_applied.emit()

    def reset_to_default(self):
        """Reset settings to the default configuration."""

        default_config = configparser.ConfigParser()
        default_config.read(self.default_config_path)

        for _, (section, key, line_edit) in self.settings_fields.items():
            line_edit.setText(default_config[section][key])

    def accept(self):
        self.apply_settings()
        super().accept()
