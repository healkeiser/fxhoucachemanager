"""Widgets module for the FX Houdini Cache Manager application.

Notes:
    Some parts are extracted from [fxgui](https://github.com/healkeiser/fxgui).
"""

# Built-in
from datetime import datetime
import logging
import re
from typing import Optional

# Third-party
from hutil.Qt.QtGui import QPixmap
from hutil.Qt.QtWidgets import QTreeWidgetItem, QStatusBar, QWidget, QLabel
from hutil.Qt.QtCore import Qt

# from hutil.Qt.QtCore import QCollator, Qt

# Internal
from fxhoucachemanager import fxstyle


# Reload modules if in debug mode
if __import__("os").getenv("DEBUG_CODE") == "1":
    __import__("importlib").reload(fxstyle)


# ? Keeping for reference
class _FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom `QTreeWidgetItem` that provides natural sorting for strings
    containing numbers using QCollator for locale-aware sorting.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.collator = QCollator()
        self.collator.setNumericMode(True)

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """

        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using QCollator
        return self.collator.compare(self.text(column), other.text(column)) < 0


class FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom `QTreeWidgetItem` that provides natural sorting for strings
    containing numbers. This is useful for sorting items like version numbers
    or other strings where numeric parts should be ordered numerically.

    For example, this class will sort the following strings in the correct
    human-friendly order:

    - "something1"
    - "something9"
    - "something17"
    - "something25"

    Instead of the default sorting order:

    - "something1"
    - "something17"
    - "something25"
    - "something9"
    """

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """

        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using the custom natural sort key
        return self._generate_natural_sort_key(
            self.text(column)
        ) < self._generate_natural_sort_key(other.text(column))

    def _generate_natural_sort_key(self, s: str) -> list:
        """Generate a sort key for natural sorting of strings containing
        numbers in a human-friendly way.

        Args:
            s: The string to sort.

        Returns:
            A list of elements where numeric parts are converted to integers
            and other parts are converted to lowercase strings.
        """

        # Split the string into parts, converting numeric parts to integers
        # and non-numeric parts to lowercase strings
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split("([0-9]+)", s)
        ]


class FXStatusBar(QStatusBar):
    """Customized QStatusBar class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `None`.
        project (str, optional): Project name. Defaults to `None`.
        version (str, optional): Version information. Defaults to `None`.
        company (str, optional): Company name. Defaults to `None`.

    Attributes:
        project (str): The project name.
        version (str): The version string.
        company (str): The company name.
        icon_label (QLabel): The icon label.
        message_label (QLabel): The message label.
        project_label (QLabel): The project label.
        version_label (QLabel): The version label.
        company_label (QLabel): The company label.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
    ):

        super().__init__(parent)

        # Attributes
        self.project = project or "Project"
        self.version = version or "0.0.0"
        self.company = company or "\u00A9 Company"
        self.icon_label = QLabel()
        self.message_label = QLabel()
        self.project_label = QLabel(self.project)
        self.version_label = QLabel(self.version)
        self.company_label = QLabel(self.company)

        self.message_label.setTextFormat(Qt.RichText)

        left_widgets = [
            self.icon_label,
            self.message_label,
        ]

        right_widgets = [
            self.project_label,
            self.version_label,
            self.company_label,
        ]

        for widget in left_widgets:
            self.addWidget(widget)
            widget.setVisible(False)  # Hide if no message is shown

        # for widget in right_widgets:
        #     self.addPermanentWidget(widget)

        self.messageChanged.connect(self._on_status_message_changed)

    def showMessage(
        self,
        message: str,
        severity_type: int = 4,
        duration: float = 2.5,
        time: bool = True,
        logger: Optional[logging.Logger] = None,
        set_color: bool = True,
        pixmap: Optional[QPixmap] = None,
        background_color: Optional[str] = None,
    ):
        """Display a message in the status bar with a specified severity.

        Args:
            message (str): The message to be displayed.
            severity_type (int, optional): The severity level of the message.
                Should be one of `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`,
                `INFO`, or `DEBUG`. Defaults to `INFO`.
            duration (float, optional): The duration in seconds for which
                the message should be displayed. Defaults to` 2.5`.
            time (bool, optional): Whether to display the current time before
                the message. Defaults to `True`.
            logger (Logger, optional): A logger object to log the message.
                Defaults to `None`.
            set_color (bool): Whether to set the status bar color depending on
                the log verbosity. Defaults to `True`.
            pixmap (QPixmap, optional): A custom pixmap to be displayed in the
                status bar. Defaults to `None`.
            background_color (str, optional): A custom background color for
                the status bar. Defaults to `None`.

        Examples:
            To display a critical error message with a red background
            >>> self.showMessage(
            ...     "Critical error occurred!",
            ...     severity_type=self.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )

        Note:
            You can either use the `FXMainWindow` instance to retrieve the
            verbosity constants, or the `fxwidgets` module.
            Overrides the base class method.
        """

        # Send fake signal to trigger the `messageChanged` event
        super().showMessage(" ", timeout=duration * 1000)

        # Show the icon and message label which were hidden at init time
        self.icon_label.setVisible(True)
        self.message_label.setVisible(True)

        colors_dict = fxstyle.load_colors_from_jsonc()
        severity_mapping = {
            0: (
                "Critical",
                None,
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            1: (
                "Error",
                None,
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            2: (
                "Warning",
                None,
                colors_dict["feedback"]["warning"]["background"],
                colors_dict["feedback"]["warning"]["dark"],
            ),
            3: (
                "Success",
                None,
                colors_dict["feedback"]["success"]["background"],
                colors_dict["feedback"]["success"]["dark"],
            ),
            4: (
                "Info",
                None,
                colors_dict["feedback"]["info"]["background"],
                colors_dict["feedback"]["info"]["dark"],
            ),
            5: (
                "Debug",
                None,
                colors_dict["feedback"]["debug"]["background"],
                colors_dict["feedback"]["debug"]["dark"],
            ),
        }

        (
            severity_prefix,
            severity_icon,
            status_bar_color,
            status_bar_border_color,
        ) = severity_mapping[severity_type]

        # Use custom pixmap if provided
        if pixmap is not None:
            severity_icon = pixmap

        # Use custom background color if provided
        if background_color is not None:
            status_bar_color = background_color

        # Message
        message_prefix = (
            f"<b>{severity_prefix}</b>: {self._get_current_time()} - "
            if time
            else f"{severity_prefix}: "
        )
        notification_message = f"{message_prefix} {message}"
        # self.icon_label.setPixmap(severity_icon)
        self.message_label.setText(notification_message)
        # self.clearMessage()

        if set_color:
            self.setStyleSheet(
                """QStatusBar {
                background: """
                + status_bar_color
                + """;
                border-top: 1px solid"""
                + status_bar_border_color
                + """;
                }
                """
            )

        # Link `Logger` object
        if logger is not None:
            # Modify log level according to severity_type
            if severity_type == 0:
                logger.critical(message)
            if severity_type == 1:
                logger.error(message)
            elif severity_type == 2:
                logger.warning(message)
            elif severity_type == 3:
                logger.info(message)
            elif severity_type == 4:
                logger.info(message)
            elif severity_type == 5:
                logger.debug(message)

    def clearMessage(self):
        """Clears the message from the status bar.

        Note:
            Overrides the base class method.
        """

        self.icon_label.clear()
        self.icon_label.setVisible(False)
        self.message_label.clear()
        self.message_label.setVisible(False)
        super().clearMessage()

    def _get_current_time(
        self, display_seconds: bool = False, display_date: bool = False
    ) -> str:
        """Returns the current time as a string.

        Args:
            display_seconds (bool, optional): Whether to display the seconds.
                Defaults to `False`.
            display_date (bool, optional): Whether to display the date.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        format_string = "%H:%M:%S" if display_seconds else "%H:%M"
        if display_date:
            format_string = "%Y-%m-%d " + format_string
        return datetime.now().strftime(format_string)

    def _on_status_message_changed(self, args):
        """If there are no arguments, which means the message is being removed,
        then change the status bar background back to black.
        """

        if not args:
            self.clearMessage()
            self.setStyleSheet(
                """
                QStatusBar {
                    border: 0px solid transparent;
                    background: #191919;
                    border-top: 1px solid black;
                }
            """
            )
