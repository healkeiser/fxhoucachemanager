# Built-in
import logging
from functools import partial
import os
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import hou
from qtpy.QtCore import QThread, Qt, QPoint
from qtpy.QtGui import QColor, QFont, QIcon
from qtpy.QtWidgets import (
    QPushButton,
    QLineEdit,
    QTreeWidget,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QMainWindow,
    QProgressBar,
    QComboBox,
    QTreeWidgetItem,
    QSpacerItem,
    QSizePolicy,
    QDialogButtonBox,
    QLabel,
    QMenu,
    QWidgetAction,
    QAbstractItemView,
    QActionGroup,
)

# Internal
from fxhoucachemanager import fxenvironment, fxmodel, fxsettings, fxwidgets
from fxhoucachemanager.utils.logger import configure_logger, set_log_level

# Reload modules if in debug mode
if os.getenv("DEBUG_CODE") == "1":
    from importlib import reload

    reload(fxmodel)
    reload(fxsettings)
    reload(fxwidgets)

# Logger
_logger = configure_logger(__name__)
_logger.setLevel(logging.DEBUG)

# Constants
CRITICAL = 0
ERROR = 1
WARNING = 2
SUCCESS = 3
INFO = 4
DEBUG = 5


class FXCacheManagerMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Configuration
        self._config = fxsettings.load_config(
            fxenvironment.FXCACHEMANAGER_USER_CONFIG_PATH
        )
        self._config_houdini_variable: str = self._config["houdini_variable"]
        self._config_cache_root_path: str = self._config["cache_root_path"]
        self._config_version_pattern: str = self._config["version_pattern"]

        # Caches data
        self.caches: Dict = {}

        # UI
        self._original_fonts: Dict = {}

        # Columns
        self._column_node: int = 0
        self._column_cache: int = 1
        self._column_version: int = 2
        self._column_path: int = 3

        # Status bar
        self.CRITICAL: int = CRITICAL
        self.ERROR: int = ERROR
        self.WARNING: int = WARNING
        self.SUCCESS: int = SUCCESS
        self.INFO: int = INFO

        # Init
        self._init_ui()
        self._update_selected_button_state()
        self._update_all_button_state()
        self._start_worker()

    def _init_ui(self):
        # Set window properties
        self.setWindowTitle("FX | Cache Manager")
        self.setWindowIcon(
            QIcon(
                str(
                    Path(__file__).parent
                    / "images"
                    / "icons"
                    / "fxhoucachemanager_dark.svg"
                )
            )
        )
        self.resize(800, 600)

        # Menu bar
        menu_bar = self.menuBar()
        edit_menu = menu_bar.addMenu("Edit")
        self.settings_action = edit_menu.addAction("Settings")
        self.settings_action.triggered.connect(self._open_settings_dialog)

        # Log level
        log_level_menu = edit_menu.addMenu("Log Level")
        log_levels = {
            "Debug": logging.DEBUG,
            "Info": logging.INFO,
            "Warning": logging.WARNING,
            "Error": logging.ERROR,
            "Critical": logging.CRITICAL,
        }

        self.log_level_actions = {}
        log_level_group = QActionGroup(self)

        for level_name, level_value in log_levels.items():
            action = log_level_menu.addAction(level_name)
            action.setCheckable(True)
            action.triggered.connect(partial(set_log_level, level_value))
            log_level_group.addAction(action)
            self.log_level_actions[level_name] = action

        # Set default log level
        self.log_level_actions["Info"].setChecked(True)
        set_log_level(logging.INFO)  # For the first time opening the app

        # Status bar
        self.status_bar = fxwidgets.FXStatusBar(
            parent=self,
        )
        self.setStatusBar(self.status_bar)

        # Create main widget and layout
        main_widget = QWidget(self)
        main_layout = QVBoxLayout(main_widget)

        # Create a horizontal layout for the icon button and search bar
        top_layout = QHBoxLayout()

        # Search bar
        search_icon_button = QPushButton(self)
        search_icon_button.setIcon(hou.qt.Icon("BUTTONS_search"))
        search_icon_button.setFixedSize(21, 21)
        search_icon_button.setStyleSheet("border: none; background: none;")

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self._filter_tree)

        top_layout.addWidget(search_icon_button)
        top_layout.addWidget(self.search_bar)

        # QTreeWidget
        self.cache_tree_widget = QTreeWidget(self)
        self.cache_tree_widget.setHeaderLabels(
            ["Node", "Cache", "Version", "Path"]
        )
        self.cache_tree_widget.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.cache_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cache_tree_widget.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self.cache_tree_widget.setSortingEnabled(True)
        self.cache_tree_widget.header().setSortIndicator(
            self.cache_tree_widget.header().sortIndicatorSection(),
            Qt.AscendingOrder,
        )

        self.cache_tree_widget.itemExpanded.connect(self._handle_item_expanded)
        self.cache_tree_widget.itemCollapsed.connect(
            self._handle_item_collapsed
        )

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed
        )

        # Update all to latest button
        self.update_all_button = QPushButton("Update All to Latest")
        self.update_all_button.clicked.connect(self._update_all_to_latest)

        # Cache extension filtering buttons
        extension_layout = QHBoxLayout()
        extension_spacer = QSpacerItem(
            1000, 20, QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        self.invalid_button = self._create_extension_filter_button(
            hou.qt.Icon("TOP_status_error"),
            self._format_tooltip("Invalid Cache", "No extension"),
        )
        self.geometry_button = self._create_extension_filter_button(
            hou.qt.Icon("OBJ_geo"),
            self._format_tooltip("Geometry Cache", ".bgeo.sc"),
        )
        self.alembic_button = self._create_extension_filter_button(
            hou.qt.Icon("SOP_alembic"),
            self._format_tooltip("Alembic Cache", ".abc"),
        )
        self.vdb_button = self._create_extension_filter_button(
            hou.qt.Icon("COMMON_openvdb"),
            self._format_tooltip("VDB Cache", ".vdb"),
        )
        self.usd_button = self._create_extension_filter_button(
            hou.qt.Icon("COMMON_usd"),
            self._format_tooltip("USD Cache", ".usd, .usda, .usdc"),
        )
        self.fbx_button = self._create_extension_filter_button(
            hou.qt.Icon("ROP_fbx"),
            self._format_tooltip("FBX Cache", ".fbx"),
        )
        self.obj_button = self._create_extension_filter_button(
            hou.qt.Icon("NETWORKS_obj"),
            self._format_tooltip("OBJ Cache", ".obj"),
        )

        extension_layout.addItem(extension_spacer)
        extension_layout.addWidget(self.invalid_button)
        extension_layout.addWidget(self.geometry_button)
        extension_layout.addWidget(self.alembic_button)
        extension_layout.addWidget(self.vdb_button)
        extension_layout.addWidget(self.usd_button)
        extension_layout.addWidget(self.fbx_button)
        extension_layout.addWidget(self.obj_button)

        self.invalid_button.setChecked(True)
        self.geometry_button.setChecked(True)
        self.alembic_button.setChecked(True)
        self.vdb_button.setChecked(True)
        self.usd_button.setChecked(True)
        self.fbx_button.setChecked(False)
        self.obj_button.setChecked(False)

        # Bottom buttons
        main_button_layout = QHBoxLayout()

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self._start_worker)

        main_button_layout.addWidget(reload_button)
        main_button_layout.addStretch(4000)

        # Update selected to latest button
        self.update_selected_button = QPushButton("Update Selected to Latest")
        self.update_selected_button.clicked.connect(
            lambda: self._update_selected_to_latest(
                self.cache_tree_widget.selectedItems()
            )
        )
        main_button_layout.addWidget(self.update_all_button)
        main_button_layout.addWidget(self.update_selected_button)

        #
        self.cache_tree_widget.itemSelectionChanged.connect(
            self._update_selected_button_state
        )
        self.cache_tree_widget.itemChanged.connect(
            self._update_all_button_state
        )
        self.cache_tree_widget.model().rowsInserted.connect(
            self._update_all_button_state
        )
        self.cache_tree_widget.model().rowsRemoved.connect(
            self._update_all_button_state
        )

        close_button_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_button_box.rejected.connect(self.close)
        main_button_layout.addWidget(close_button_box)

        # Add to the main layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.cache_tree_widget)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(extension_layout)
        main_layout.addLayout(main_button_layout)

        # Set the layout to the main window
        self.setCentralWidget(main_widget)

    def statusBar(self) -> fxwidgets.FXStatusBar:
        """Returns the FXStatusBar instance associated with this window.

        Returns:
            FXStatusBar: The FXStatusBar instance associated with this window.

        Note:
            Overrides the base class method.
        """

        return self.status_bar

    def _open_settings_dialog(self):
        dialog = fxsettings.FXSettingsDialog(self)
        dialog.settings_applied.connect(self._update_settings)
        dialog.settings_applied.connect(self._start_worker)
        dialog.exec_()

    def _update_settings(self):
        self._config = fxsettings.load_config(
            fxenvironment.FXCACHEMANAGER_USER_CONFIG_PATH
        )
        self._config_houdini_variable = self._config["houdini_variable"]
        self._config_cache_root_path = self._config["cache_root_path"]
        self._config_version_pattern = self._config["version_pattern"]

    def _update_selected_button_state(self):
        """Enable or disable the button Update Selected based on the presence
        of selected items in the tree.
        """

        selected_items = self.cache_tree_widget.selectedItems()
        self.update_selected_button.setEnabled(bool(selected_items))

    def _update_all_button_state(self):
        """Enable or disable the Update All button based on the presence
        of visible items in the tree."""

        has_visible_items = any(
            not self.cache_tree_widget.topLevelItem(i).isHidden()
            for i in range(self.cache_tree_widget.topLevelItemCount())
        )

        self.update_all_button.setEnabled(has_visible_items)

    # ' Get caches data
    def _stop_current_worker(self) -> None:
        """Stop the current worker thread if it is running."""

        if hasattr(self, "_thread") and hasattr(self, "_worker"):
            try:
                self._worker.finished.disconnect(self._stop_worker)
                self._worker.finished.disconnect(self._thread.quit)
                self._worker.finished.disconnect(self._worker.deleteLater)
            except RuntimeError:
                # The worker object might already be deleted
                pass

            try:
                self._thread.finished.disconnect(self._thread.deleteLater)
                self._thread.quit()
                self._thread.wait()
            except RuntimeError:
                # The thread object might already be deleted
                pass

    def _reset_progress_bar(self) -> None:
        """Reset the progress bar to its initial state."""

        self.progress_bar.setValue(0)
        self.progress_bar.setHidden(True)

    def _start_worker(self) -> None:
        """Start the worker to get the caches data."""

        # Stop the current worker if it is running
        self._stop_current_worker()

        # Save tree expansion state
        self._save_expansion_state()

        # Reset the progress bar
        self._reset_progress_bar()

        # Start the data retrieval in a separate thread to avoid
        # freezing the UI when scanning the caches
        self._thread = QThread()
        self._worker = fxmodel.FXGatherCacheDataObject(
            self,
            self._config_houdini_variable,
            self._config_cache_root_path,
            self._config_version_pattern,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._update_worker_progress)
        self._worker.finished.connect(self._stop_worker)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _update_worker_progress(self, value: int) -> None:
        """Update the progress bar value of the cache worker.

        Args:
            value: The progress value.
        """

        self.progress_bar.setValue(value)

    def _stop_worker(self, caches: Dict) -> None:
        """Stop the cache worker and update the caches data.

        Args:
            caches: The caches data.
        """

        # Update the class attribute holding the cache data
        self.caches = caches

        # Restore tree expansion state
        self._restore_expansion_state()

        # Populate the tree based on the caches data we just retrieved
        self._populate_tree()

        # Reset the progress bar
        self._reset_progress_bar()

        self.statusBar().showMessage(
            "Loaded cache data", self.INFO, logger=_logger
        )

    # ' Filter tree
    def _filter_item(
        self,
        item: QTreeWidgetItem,
        text: str,
        selected_extensions: list,
        show_invalid: bool,
    ) -> bool:
        """Recursively filter tree items.

        Args:
            item: The item to filter.
            text: The text to search for.
            selected_extensions: The list of selected extensions.
            show_invalid: Whether to show invalid paths.

        Returns:
            `True` if the text is found and the extension is selected,
            `False` otherwise.
        """

        # Check if the text is in any of the columns
        columns = 2
        text_lower = text.lower()
        match = any(
            text_lower in item.text(col).lower() for col in range(columns)
        )

        # Check if the item's extension is in the selected extensions
        cache_extension = item.text(self._column_cache)
        extension_match = any(
            extension in cache_extension for extension in selected_extensions
        )

        # Check if the item is invalid
        is_invalid = not item.data(0, Qt.UserRole)

        # Recursively check the children and compare the result
        for i in range(item.childCount()):
            child = item.child(i)
            match = (
                self._filter_item(
                    child, text, selected_extensions, show_invalid
                )
                or match
            )

        # Hide the item if it doesn't match the search criteria
        item.setHidden(
            not (match and (extension_match or (show_invalid and is_invalid)))
        )
        return match and (extension_match or (show_invalid and is_invalid))

    def _filter_tree(self, text: str = "") -> None:
        """Filter the tree based on the search bar input and selected
        extensions.

        Args:
            text: The text to search for. Defaults to `""`.
        """

        selected_extensions = self._get_selected_extensions()
        show_invalid = self.invalid_button.isChecked()

        for i in range(self.cache_tree_widget.topLevelItemCount()):
            item = self.cache_tree_widget.topLevelItem(i)
            self._filter_item(item, text, selected_extensions, show_invalid)

    def _filter_tree_by_extension(self):
        """Filter the tree widget items based on the selected extensions."""

        self._filter_tree(self.search_bar.text())

        # Update the button states, so the user can't update caches that don't
        # have the selected extensions
        self._update_all_button_state()

    def _get_selected_extensions(self) -> list:
        """Get the list of selected extensions."""

        selected_extensions = []
        if self.geometry_button.isChecked():
            selected_extensions.append(".bgeo.sc")
        if self.alembic_button.isChecked():
            selected_extensions.append(".abc")
        if self.usd_button.isChecked():
            selected_extensions.extend([".usd", ".usda", ".usdc"])
        if self.vdb_button.isChecked():
            selected_extensions.append(".vdb")
        if self.fbx_button.isChecked():
            selected_extensions.append(".fbx")
        if self.obj_button.isChecked():
            selected_extensions.append(".obj")
        return selected_extensions

    def _create_extension_filter_button(
        self, icon: QIcon, tooltip: str
    ) -> QPushButton:
        """Create a button for filtering the tree by extension.

        Args:
            icon: The icon to display on the button.
            tooltip: The tooltip to display when hovering over the button.

        Returns:
            The created button.
        """

        button = QPushButton()
        button.setCheckable(True)
        button.setFixedWidth(25)
        button.setIcon(icon)
        button.setToolTip(tooltip)
        button.toggled.connect(self._filter_tree_by_extension)
        return button

    # ' Tree widget
    def _save_expansion_state(self):
        """Save the expansion state of the tree using unique identifiers.
        We use a unique identifier, in this case the text in the first column,
        to store the expansion state. This allows us to restore the expansion
        state later on, even if the item gets deleted and recreated
        (which happens when the caches are updated).
        """

        self._expansion_state = {}
        root = self.cache_tree_widget.invisibleRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item.childCount() > 0:
                identifier = item.text(self._column_node)
                self._expansion_state[identifier] = item.isExpanded()
                for i in range(item.childCount()):
                    stack.append(item.child(i))

    def _restore_expansion_state(self):
        """Restore the expansion state of the tree using unique identifiers."""

        if not hasattr(self, "_expansion_state"):
            return
        root = self.cache_tree_widget.invisibleRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item.childCount() > 0:
                identifier = item.text(self._column_node)
                if identifier in self._expansion_state:
                    item.setExpanded(self._expansion_state[identifier])
                for i in range(item.childCount()):
                    stack.append(item.child(i))

    def _handle_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Make the font of the expanded parent item bold, so it's easier to
        see which item is the currently referenced cache.

        Args:
            item: The expanded item.
        """

        # Check the item is a top-level item and has children
        if not item.parent() and item.childCount() > 0:
            self._original_fonts[item] = [
                item.font(i) for i in range(item.columnCount())
            ]

            font = item.font(0)
            font.setBold(True)
            for i in range(item.columnCount()):
                item.setFont(i, font)

    def _handle_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """Revert the font of the collapsed item to their original state.

        Args:
            item: The collapsed item.
        """

        if item in self._original_fonts:
            for i, font in enumerate(self._original_fonts[item]):
                item.setFont(i, font)

            del self._original_fonts[item]

    def _create_tree_item(
        self,
        cache_text: str,
        valid_cache_file: bool = True,
        valid_cache_path: bool = True,
        node_name: Optional[str] = None,
        node: Optional[hou.Node] = None,
        icon: Optional[QIcon] = None,
        color_foreground: Optional[QColor] = None,
        color_background: Optional[QColor] = None,
        version: Optional[str] = None,
        path: Optional[str] = None,
        extension: Optional[str] = None,
    ) -> QTreeWidgetItem:
        """Create a QTreeWidgetItem with the given parameters.

        Args:
            cache_text: The text to display in the cache column.
            valid_cache_file: Whether the cache file is valid or not.
            valid_cache_path: Whether the cache path is valid or not.
            node_name: The name of the node.
            node: The node object, which is used to retrieve the.
            icon: The icon to display in the cache column.
            color_foreground: The color to set for the cache text.
            color_background: The color to set for the item background.
            version: The version of the cache.
            path: The path of the cache.
            extension: The extension of the cache.

        Returns:
            The created tree widget item.
        """

        # item = QTreeWidgetItem()
        item = fxwidgets.FXSortedTreeWidgetItem()

        # Set user data for cache validity, so we can retrieve it
        # easily later on
        item.setData(0, Qt.UserRole, valid_cache_file)
        item.setData(1, Qt.UserRole, valid_cache_path)

        # Node column
        if node_name:
            item.setText(self._column_node, node_name)
        if node:
            item.setIcon(self._column_node, hou.qt.Icon(node.type().icon()))
        font_bold: QFont = QFont()
        font_bold.setBold(True)
        item.setFont(self._column_node, font_bold)
        item.setToolTip(
            self._column_node,
            self._format_tooltip(
                title=node_name,
                message="Node Path: " + node.path() if node else "",
            ),
        )

        # Cache column
        item.setText(self._column_cache, cache_text)
        if icon:
            item.setIcon(self._column_cache, icon)
        if color_foreground:
            item.setForeground(self._column_cache, color_foreground)
        message_parts = []
        if version:
            message_parts.append(f"Version: <b>{version}</b><br><br>")
        if extension:
            message_parts.append(f"Extension: <b>{extension}</b>")
        if path:
            message_parts.append(f"<br><br>Path: <b><i>{path}</i></b>")
        item.setToolTip(
            self._column_cache,
            self._format_tooltip(
                title=cache_text,
                message="".join(message_parts),
            ),
        )

        # Version column
        if version:
            item.setText(self._column_version, version)

        # Path column
        if path:
            item.setText(self._column_path, path)
        item.setForeground(self._column_path, QColor("#858585"))
        font_italic: QFont = QFont()
        font_italic.setItalic(True)
        item.setFont(self._column_path, font_italic)

        # All columns
        if color_background:
            for i in range(item.columnCount()):
                item.setBackground(i, color_background)

        return item

    def _format_tooltip(
        self, title: str, message: Optional[str] = None
    ) -> str:
        """Format a tooltip with a title and a message.

        Args:
            title: The title of the tooltip.
            message: The message of the tooltip.
        """

        return f"<b>{title}</b>{'<hr>' + message if message else ''}"

    def _set_version_ui(
        self, item: QTreeWidgetItem, version: str, latest_version: str
    ) -> None:
        """Set the UI properties of a tree item based on its cache version
        state (up-to date or outdated).

        Args:
            item: The tree widget item to update.
            version: The current version of the cache.
            latest_version: The latest version of the cache.
        """

        if version == latest_version and not version is None:
            color_green = QColor("#8ac549")
            item.setForeground(self._column_cache, color_green)
            item.setForeground(self._column_version, color_green)
            item.setIcon(self._column_cache, hou.qt.Icon("TOP_status_cooked"))
        elif version != latest_version and not version is None:
            color_orange = QColor("#ffbb33")
            item.setForeground(self._column_cache, color_orange)
            item.setForeground(self._column_version, color_orange)
            item.setIcon(
                self._column_cache, hou.qt.Icon("TOP_status_canceled")
            )
        else:
            color_blue_grey = QColor("#afd2e1")
            item.setForeground(self._column_cache, color_blue_grey)
            item.setForeground(self._column_version, color_blue_grey)
            item.setIcon(
                self._column_cache, hou.qt.Icon("TOP_status_unstarted")
            )

    def _resize_tree_columns_to_content(self, tree: QTreeWidget) -> None:
        """Resize all columns to fit their content automatically."""

        for column in range(tree.columnCount()):
            tree.resizeColumnToContents(column)

    def _populate_tree(self) -> None:
        """Populate the tree widget with the caches data."""

        # Clear the tree and the `_original_fonts` dictionary
        self.cache_tree_widget.clear()

        # Populate the tree based on the caches data stored in `self.caches`
        for node_name, cache_data_dict in self.caches.items():
            # Create an instance of `FXCacheData`
            node = cache_data_dict.get("cache_node")
            referenced_parm = cache_data_dict.get("cache_parm")
            used_cache_path = Path(cache_data_dict.get("cache_name"))

            cache_data = fxmodel.FXCacheData(
                node, referenced_parm, used_cache_path
            )
            cache_data.update(cache_data_dict)

            valid_cache_file = cache_data.data["valid_cache_file"]
            valid_cache_path = cache_data.data["valid_cache_path"]

            if not valid_cache_file:
                # Create and add an item for invalid cache files, so the user
                # still has feedback about the missing cache files
                used_cache_item = self._create_tree_item(
                    cache_text="Invalid Cache",
                    valid_cache_file=valid_cache_file,
                    valid_cache_path=valid_cache_path,
                    node_name=node_name,
                    node=node,
                    icon=hou.qt.Icon("TOP_status_error"),
                    color_foreground=QColor("#ff4444"),
                )
                self.cache_tree_widget.addTopLevelItem(used_cache_item)
                continue

            # Retrieve the cache data
            used_cache_path = next(iter(cache_data.data["used_cache_path"]))
            unused_cache_paths = cache_data.data["unused_cache_paths"]
            all_versions = cache_data.data["all_versions"]
            latest_version = cache_data.data["latest_version"]
            current_version = cache_data.data["current_version"]
            extension = cache_data.data["cache_extension"]

            # Create and add an item for the used cache (parent item)
            used_cache_item = self._create_tree_item(
                cache_text=used_cache_path.name,
                valid_cache_file=valid_cache_file,
                valid_cache_path=valid_cache_path,
                node_name=node_name,
                node=node,
                version=current_version,
                path=used_cache_path.as_posix(),
                extension=extension,
            )

            self._set_version_ui(
                used_cache_item, current_version, latest_version
            )
            self.cache_tree_widget.addTopLevelItem(used_cache_item)

            # Create and set the version combobox, so the user can switch
            # between different cache versions
            if valid_cache_path:
                version_combobox = QComboBox()
                version_combobox.addItems(all_versions)
                version_combobox.setCurrentText(current_version)
                version_combobox.currentTextChanged.connect(
                    partial(self._update_caches, node_name)
                )
                version_combobox.setFixedHeight(19)
                self.cache_tree_widget.setItemWidget(
                    used_cache_item, self._column_version, version_combobox
                )

            # Create and add items for unused caches (they are children of the
            # used cache item)
            for unused_cache_path, version in unused_cache_paths.items():
                unused_cache_item = self._create_tree_item(
                    cache_text=unused_cache_path.name,
                    valid_cache_file=valid_cache_file,
                    valid_cache_path=valid_cache_path,
                    version=version,
                    color_background=QColor("#3a3a3a"),
                    path=unused_cache_path.as_posix(),
                    extension=extension,
                )
                self._set_version_ui(
                    unused_cache_item, version, latest_version
                )

                # Make the unused cache items unselectable
                # This way the context menu will still be able to use the
                # actions when the item is right-clicked, but the item itself
                # will not be selectable -> that avoids errors when trying to
                # update all caches to the latest version
                unused_cache_item.setFlags(
                    unused_cache_item.flags() & ~Qt.ItemIsSelectable
                )

                used_cache_item.addChild(unused_cache_item)

        # Filter the tree based on the search bar input and selected extensions
        self._filter_tree(self.search_bar.text())

        # Resize all columns to fit their content automatically
        for i in range(self.cache_tree_widget.columnCount()):
            self.cache_tree_widget.resizeColumnToContents(i)

    def _update_caches(self, node_name: str, new_version: str) -> None:
        """Update the caches dictionary and the UI when the version combobox
        changes.

        Args:
            node_name: The name of the node, which is the key in the
                `caches` dictionary.
            new_version: The new version selected in the combobox.
        """

        # Retrieve the cache data
        cache_data_dict = self.caches[node_name]
        node = cache_data_dict.get("cache_node")
        referenced_parm = cache_data_dict.get("cache_parm")
        used_cache_path = Path(cache_data_dict.get("cache_name"))

        cache_data = fxmodel.FXCacheData(
            node, referenced_parm, used_cache_path
        )
        cache_data.update(cache_data_dict)

        cache_name = cache_data.data["cache_name"]
        current_version = cache_data.data["current_version"]
        latest_version = cache_data.data["latest_version"]
        is_current_latest = new_version == latest_version
        old_used_cache_path = next(iter(cache_data.data["used_cache_path"]))
        new_used_cache_path = next(
            path
            for path, version in cache_data.data["unused_cache_paths"].items()
            if version == new_version
        )

        # Update the cache data
        cache_data.data["unused_cache_paths"].pop(new_used_cache_path)
        cache_data.data["unused_cache_paths"][
            old_used_cache_path
        ] = current_version
        cache_data.data["used_cache_path"] = {new_used_cache_path: new_version}
        cache_data.data["current_version"] = new_version
        cache_data.data["is_current_latest"] = is_current_latest

        # Sort the `unused_cache_paths` dictionary by version in descending order
        cache_data.data["unused_cache_paths"] = dict(
            sorted(
                cache_data.data["unused_cache_paths"].items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

        # Update the class attribute holding the cache data
        self.caches[node_name] = cache_data.get_data()

        # Find the parent item (used cache) in the tree widget
        root_items = [
            self.cache_tree_widget.topLevelItem(i)
            for i in range(self.cache_tree_widget.topLevelItemCount())
        ]
        used_cache_item = next(
            item
            for item in root_items
            if item.text(self._column_node) == node_name
        )

        # Update the parent item
        used_cache_item.setText(self._column_version, new_version)
        used_cache_item.setText(
            self._column_path, new_used_cache_path.as_posix()
        )
        self._set_version_ui(used_cache_item, new_version, latest_version)

        # Update the Houdini node parm with the new cache path
        cache_parm = cache_data.data["cache_parm"]
        collasped_new_used_cache_path = self._collapse_houdini_path(
            new_used_cache_path, node_name
        )
        message = f"Set cache '{cache_name}' from version '{current_version}' to '{new_version}'"
        self.statusBar().showMessage(message, self.SUCCESS, logger=_logger)

        # Add an undo group for the update cache path operation, so the label
        # in the undo history is more descriptive
        with hou.undos.group("Update Cache Path"):
            cache_parm.set(collasped_new_used_cache_path)

        # Update the child (unused cache) items
        used_cache_item.takeChildren().clear()
        for path, version in cache_data.data["unused_cache_paths"].items():
            unused_cache_item = self._create_tree_item(
                cache_text=path.name,
                version=version,
                path=path.as_posix(),
                color_background=QColor("#3a3a3a"),
            )
            self._set_version_ui(unused_cache_item, version, latest_version)
            used_cache_item.addChild(unused_cache_item)

        # Resize columns to fit their content automatically
        self._resize_tree_columns_to_content(self.cache_tree_widget)

    # ' Context menu and actions
    def _show_context_menu(self, position: QPoint) -> None:
        """Show the context menu when right-clicking on an item.

        Args:
            position: The position of the right-click.
        """

        # Retrieve the item at the clicked position
        item = self.cache_tree_widget.itemAt(position)

        # Create the context menu
        menu: QMenu = hou.qt.Menu()

        # Add a label title
        label = QLabel(
            item.text(self._column_cache) if item else "Cache Manager"
        )
        label.setMargin(2)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: #2b2b2b; color: white;")
        label_action = QWidgetAction(menu)
        label_action.setDefaultWidget(label)
        menu.addAction(label_action)

        # Add actions
        action_show_in_explorer = menu.addAction("Show in Explorer")
        menu.addSeparator()
        action_go_to_node = menu.addAction("Go to Node")
        menu.addSeparator()
        action_update_selected_to_latest = menu.addAction(
            "Update Selected to Latest"
        )
        action_update_all_to_latest = menu.addAction("Update All to Latest")
        menu.addSeparator()
        action_delete_unused_caches = menu.addAction("Delete Unused Caches")
        menu.addSeparator()
        action_expand_all = menu.addAction("Expand All")
        action_collapse_all = menu.addAction("Collapse All")

        # Enable or disable actions based on the selected item
        if item:
            is_parent = not item.parent()
            is_cache_file_valid = item.data(0, Qt.UserRole)
            is_cache_path_valid = item.data(1, Qt.UserRole)
            action_show_in_explorer.setEnabled(is_cache_file_valid)
            action_go_to_node.setEnabled(is_parent)
            action_update_selected_to_latest.setEnabled(
                is_parent and is_cache_file_valid and is_cache_path_valid
            )
            action_delete_unused_caches.setEnabled(
                is_parent and is_cache_file_valid and is_cache_path_valid
            )
        else:
            action_show_in_explorer.setEnabled(False)
            action_go_to_node.setEnabled(False)
            action_update_selected_to_latest.setEnabled(False)
            action_delete_unused_caches.setEnabled(False)

        # Execute the selected action
        action = menu.exec_(
            self.cache_tree_widget.viewport().mapToGlobal(position)
        )

        # Map actions to functions
        action_map = {
            action_show_in_explorer: partial(self._show_in_explorer, item),
            action_go_to_node: partial(self._go_to_node, item),
            action_update_selected_to_latest: partial(
                self._update_selected_to_latest,
                self.cache_tree_widget.selectedItems(),
            ),
            action_update_all_to_latest: self._update_all_to_latest,
            action_delete_unused_caches: partial(
                self._delete_unused_caches, item
            ),
            action_expand_all: self.cache_tree_widget.expandAll,
            action_collapse_all: self.cache_tree_widget.collapseAll,
        }

        # Call the corresponding function from the dictionary
        if action in action_map:
            action_map[action]()

    def _show_in_explorer(self, item: QTreeWidgetItem) -> None:
        """Show the cache file in the file explorer.

        Args:
            item: The item to show in the file explorer.
        """

        # No need to check for the validity of the cache file, as the
        # action is only available for valid cache files
        hou.ui.showInFileBrowser(item.text(self._column_path))

    def _go_to_node(self, item: QTreeWidgetItem) -> None:
        """Select the node in the Houdini Network Editor, then zoom onto
        the selection.

        Args:
            item: The item holding the node information.
        """

        node_name = item.text(self._column_node)
        node = self.caches[node_name]["cache_node"]
        network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        network_editor.setCurrentNode(node)
        network_editor.homeToSelection()

    def _is_combobox_up_to_date(self, combobox: QComboBox) -> bool:
        """Check if the combobox is up-to-date.

        Args:
            combobox: The combobox to check.

        Returns:
            `True` if the combobox is up-to-date, `False` otherwise.
        """

        return combobox.currentText() == combobox.itemText(
            combobox.count() - 1
        )

    def _update_combobox_to_latest(self, combobox: QComboBox) -> None:
        """Update the combobox to the latest version.

        Args:
            combobox: The combobox to update.
        """

        combobox.setCurrentIndex(combobox.count() - 1)

    def _update_selected_to_latest(self, items: List[QTreeWidgetItem]) -> None:
        """Update the selected caches to their latest version.

        Args:
            items: A list of selected items.
        """

        for item in items:
            widget = self.cache_tree_widget.itemWidget(
                item, self._column_version
            )
            if isinstance(widget, QComboBox):
                combobox: QComboBox = widget
                if self._is_combobox_up_to_date(combobox):
                    message = (
                        f"The cache '{item.text(self._column_cache)}' "
                        "is up-to-date"
                    )
                    self.statusBar().showMessage(
                        message, self.INFO, logger=_logger
                    )

                    continue
                self._update_combobox_to_latest(combobox)

            else:
                message = (
                    "No version to update to for "
                    f"'{item.text(self._column_cache)}'"
                )
                self.statusBar().showMessage(
                    message, self.INFO, logger=_logger
                )

    def _update_all_to_latest(self) -> None:
        """Update all caches to the latest version."""

        # Get the caches to update
        caches_to_update = {
            node_name: (
                cache_data["cache_name"],
                cache_data["current_version"],
                cache_data["latest_version"],
            )
            for node_name, cache_data in self.caches.items()
            if cache_data["current_version"] != cache_data["latest_version"]
            and not self._is_item_hidden(node_name)
        }

        # Handle the case where there are no caches to update
        if not caches_to_update:
            message = "All caches are up-to-date"
            self.statusBar().showMessage(message, self.INFO, logger=_logger)
            return

        # If there are caches to update, asks the user for confirmation
        # before updating them
        len_caches_to_update = len(caches_to_update)
        confirm = hou.ui.displayMessage(
            text=f"Are you sure you want to update {len_caches_to_update} cache(s) to the latest version?",
            default_choice=0,
            close_choice=1,
            title="Update All to Latest",
            buttons=("Update", "Cancel"),
            details="\n".join(
                [
                    f"{cache_name}: {current_version} > {latest_version}"
                    for _, (
                        cache_name,
                        current_version,
                        latest_version,
                    ) in caches_to_update.items()
                ]
            ),
            details_label="Show cache(s) to update",
            details_expanded=False,
            severity=hou.severityType.Warning,
        )
        if confirm != 0:
            return

        # Update the caches to the latest version
        self._update_comboboxes_to_latest()

        self.statusBar().showMessage(
            f"Updated {len_caches_to_update} cache(s) to the latest version",
            self.SUCCESS,
            logger=_logger,
        )

    def _is_item_hidden(self, node_name: str) -> bool:
        """Check if the item corresponding to the given node name is hidden.

        Args:
            node_name: The name of the node.

        Returns:
            `True` if the item is hidden, `False` otherwise.
        """

        for i in range(self.cache_tree_widget.topLevelItemCount()):
            item = self.cache_tree_widget.topLevelItem(i)
            if item.text(self._column_node) == node_name:
                return item.isHidden()
        return False

    def _update_comboboxes_to_latest(self) -> None:
        """Update all comboboxes to the latest version, by simply selecting
        the last item in the comboboxe item list.
        """

        for i in range(self.cache_tree_widget.topLevelItemCount()):
            parent_item = self.cache_tree_widget.topLevelItem(i)
            widget = self.cache_tree_widget.itemWidget(
                parent_item, self._column_version
            )
            if isinstance(widget, QComboBox):
                combobox: QComboBox = widget
                if not self._is_combobox_up_to_date(combobox):
                    self._update_combobox_to_latest(combobox)

    def _delete_unused_caches(self, item: QTreeWidgetItem) -> None:
        """Delete all unused caches, if their versions is under the
        current selected version (aka referenced cache in current scene).

        Args:
            item: The item to delete the unused caches for.
        """

        # Retrieve the cache data
        node_name = item.text(self._column_node)
        cache_data_dict = self.caches[node_name]
        node = cache_data_dict.get("cache_node")
        referenced_parm = cache_data_dict.get("cache_parm")
        used_cache_path = Path(cache_data_dict.get("cache_name"))

        cache_data = fxmodel.FXCacheData(
            node, referenced_parm, used_cache_path
        )
        cache_data.update(cache_data_dict)

        current_version = cache_data.data["current_version"]

        # Get the versions to delete (versions under the current version)
        paths_to_delete = [
            path
            for path, version in cache_data.data["unused_cache_paths"].items()
            if version < current_version
        ]

        # Handle the case where there are no versions to delete (the current
        # version is the only one)
        if not paths_to_delete:
            message = "No unused caches to delete"
            self.statusBar().showMessage(message, self.INFO, logger=_logger)
            return

        # Asks the user for confirmation before deleting the caches
        confirm = hou.ui.displayMessage(
            text=f"Are you sure you want to delete "
            f"{len(paths_to_delete)} cache(s) under the "
            f"version '{current_version}' for "
            f"'{item.text(self._column_cache)}'?",
            default_choice=1,
            close_choice=1,
            title="Delete Unused Caches",
            buttons=("Delete", "Cancel"),
            details="\n".join([path.as_posix() for path in paths_to_delete]),
            details_label="Show cache(s) to delete",
            details_expanded=False,
            severity=hou.severityType.Warning,
        )
        if confirm != 0:
            return

        # Same as for the `run()` method, we need to check if the _logger is
        # enabled for the DEBUG level to squeeze some performance out of the
        # loop
        if _logger.isEnabledFor(logging.DEBUG):
            for path in paths_to_delete:
                _logger.debug("Deleting cache: %s", path.as_posix())

        # Remove items from the tree and update the `self.caches` dictionary
        for path in paths_to_delete:
            # Remove from tree
            for i in range(item.childCount()):
                child = item.child(i)
                if child.text(self._column_path) == path.as_posix():
                    item.removeChild(child)
                    break

            # Remove from `self.caches`
            del cache_data.data["unused_cache_paths"][path]

            # Delete the file
            path.unlink()

        # Update the class attribute holding the cache data
        self.caches[node_name] = cache_data.get_data()

    # ' Miscellaneous
    def _collapse_houdini_path(self, path: Path, node_name: str) -> str:
        """Collapse the Houdini path with found environment variables,
        and replace the node name with the `$OS` variable.

        Args:
            path: The path to collapse.
            node_name: The name of the node to replace in the path.

        Returns:
            The collapsed path.
        """

        return hou.text.collapseCommonVars(path.as_posix()).replace(
            node_name, "$OS"
        )

    def closeEvent(self, _):  # pylint: disable=invalid-name
        """Event triggered when the widget is closed.

        Note:
            Overriding base class method.
        """

        self._stop_current_worker()
        self.setParent(None)
