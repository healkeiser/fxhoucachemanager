"""Model part for the FX Cache Manager tool."""

# Built-in
from collections import defaultdict
import os
import re
import logging
import json
from pathlib import Path
import time
from typing import Any, Dict, Generator, List, Union

# Third-party
import hou
from hutil.Qt.QtCore import QObject, Signal

# Internal
from fxhoucachemanager import fxview, fxsettings, fxenvironment
from fxhoucachemanager.utils.logger import configure_logger


# Reload modules if in debug mode
if os.getenv("DEBUG_CODE") == "1":
    from importlib import reload

    reload(fxsettings)

# Logger
_logger = configure_logger(__name__)
_logger.setLevel(logging.DEBUG)


def scan_directory(directory: str) -> Generator[str, None, None]:
    """Recursively scans a directory and yields file paths.

    Args:
        directory: The directory to scan.

    Yields:
        str: The path of each file found in the directory.
    """

    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            yield from scan_directory(entry.path)
        else:
            yield entry.path


def convert_to_serializable(obj: Any) -> Union[str, Any]:
    """Convert non-serializable objects to a serializable format.

    Args:
        obj: The object to convert.

    Returns:
        The serializable representation of the object.
    """

    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, hou.Node):
        return obj.path()
    if isinstance(obj, hou.Parm):
        return obj.name()
    return obj


def make_serializable(data: Any) -> Any:
    """Recursively convert all elements in the data to a serializable format.

    Args:
        data: The data to convert, which can be a dictionary, list, or any
            other type.

    Returns:
        The serializable representation of the data.
    """

    if isinstance(data, dict):
        return {
            str(key): make_serializable(value) for key, value in data.items()
        }
    if isinstance(data, list):
        return [make_serializable(element) for element in data]
    return convert_to_serializable(data)


class FXCacheData:
    def __init__(self, node, referenced_parm, used_cache_path):
        self.data = defaultdict(lambda: None)
        self.data.update(
            {
                "cache_node": node,
                "cache_parm": referenced_parm,
                "cache_name": used_cache_path.name,
                "cache_extension": "".join(used_cache_path.suffixes),
                "used_cache_path": {used_cache_path: None},
                "unused_cache_paths": {},
                "latest_version": None,
                "current_version": None,
                "all_versions": [],
                "is_current_latest": False,
                "valid_cache_file": used_cache_path.exists(),
                "valid_cache_path": False,
            }
        )

    def update(self, updates: Dict) -> None:
        """Update the cache data with the provided updates.

        Args:
            updates: A dictionary containing the updates to apply.
        """

        self.data.update(updates)

    def get_data(self) -> Dict:
        """Get the cache data as a dictionary.

        Returns:
            A dictionary containing the cache data.
        """

        return dict(self.data)


class FXGatherCacheDataObject(QObject):
    """Worker to get the caches data in a separate thread.

    Attributes:
        houdini_variable: The Houdini environment variable to search from.
        cache_root_path: The root path where the caches are stored.
    """

    progress = Signal(int)
    finished = Signal(dict)

    def __init__(
        self,
        parent: "fxview.FXCacheManagerMainWindow",
        houdini_variable: str,
        cache_root_path: Union[str, Path],
        version_pattern: str,
    ):
        """Initialize the worker."""

        super().__init__(parent)
        self.houdini_variable = houdini_variable or None
        self.cache_root_path = Path(cache_root_path)
        self.version_pattern = version_pattern
        self.compiled_version_pattern = re.compile(version_pattern)

        _logger.debug("\n\n" + "-" * 80 + "\n")
        _logger.debug("Houdini variable: %s", self.houdini_variable)
        _logger.debug("Cache root path: %s", self.cache_root_path)
        _logger.debug("Version pattern: %s", self.version_pattern)

    def _extract_version(self, path: Path) -> str:
        """Extract the version part from a single `Path` object.

        Args:
            path: The file path as a `Path` object.

        Returns:
            The version string if found, otherwise an empty string.
        """

        match = self.compiled_version_pattern.search(path.as_posix())
        if match:
            return match.group(0)
        return ""

    def run(self) -> None:
        """Build a dictionary with all the necessary caches data."""

        start_time = time.time()
        file_references = (
            hou.fileReferences(self.houdini_variable, include_all_refs=True)
            if self.houdini_variable
            else hou.fileReferences(include_all_refs=True)
        )

        caches = {}

        filtered_file_references = self._filter_file_references(
            file_references
        )
        total_files = len(filtered_file_references)

        for index, (referenced_parm, used_cache_path) in enumerate(
            filtered_file_references
        ):
            cache_data = self._build_cache_data(
                referenced_parm, used_cache_path
            )
            caches[referenced_parm.node().name()] = cache_data

            progress = int((index + 1) / total_files * 100)
            self.progress.emit(progress)

            _logger.debug(
                "Progress: %3d%%, cache: '%s' (%d/%d)",
                progress,
                used_cache_path.as_posix(),
                index + 1,
                total_files,
            )

        elapsed_time = time.time() - start_time
        _logger.debug(
            "Time taken to process %d cache(s): %.2f seconds",
            total_files,
            elapsed_time,
        )

        # Convert the caches dictionary to a serializable format
        if os.getenv("DEBUG_CODE") == "1":
            serializable_caches = make_serializable(caches)
            output_path = fxenvironment.FXCACHEMANAGER_DATA_DIR / "caches.json"
            with open(output_path, "w") as json_file:
                json.dump(serializable_caches, json_file, indent=4)

        self.finished.emit(caches)

    def _filter_file_references(self, file_references: List) -> List:
        """Filter and sort file references to remove duplicates.

        Args:
            file_references: A list of file references from
                `hou.fileReferences()`.

        Returns:
            A list of filtered and sorted file references.
        """

        # Pre-filter `file_references` to remove duplicates
        # Since the `hou.fileReferences()` returns all parameters with a file
        # reference, we need to get the "master" reference parm and its value
        # to get the unique file reference, and the node that controls it
        filtered_file_references = sorted(
            {
                (
                    parm.getReferencedParm(),
                    Path(parm.getReferencedParm().eval()),
                )
                for parm, _ in file_references
                if isinstance(parm, hou.Parm)
                and Path(parm.getReferencedParm().eval()).is_relative_to(
                    self.cache_root_path
                )
            },
            # Sort with `used_cache_path` (mostly for debug output purposes)
            key=lambda x: str(x[1]),
        )

        _logger.debug("Number files referenced: %d", len(file_references))
        _logger.debug(
            "Number filtered files referenced: %d",
            len(filtered_file_references),
        )

        return filtered_file_references

    def _build_cache_data(
        self, referenced_parm: hou.Parm, used_cache_path: Path
    ) -> Dict:
        """Build cache data for a single file reference.

        Args:
            referenced_parm: The referenced parameter.
            used_cache_path: The used cache path.

        Returns:
            A dictionary containing the cache data.
        """

        # Get the node associated with the referenced parameter
        node = referenced_parm.node()

        # Initialize CacheData object
        cache_data = FXCacheData(node, referenced_parm, used_cache_path)

        # Return early if the used cache path does not exist
        if not used_cache_path.exists():
            return cache_data.get_data()

        # Check if the parent directory of the used cache path matches the version pattern
        if not bool(
            self.compiled_version_pattern.match(used_cache_path.parent.name)
        ):
            _logger.warning(
                "Cache path parent directory '%s' is not a version directory: '%s'",
                used_cache_path.name,
                used_cache_path.parent.name,
            )
            return cache_data.get_data()

        # Scan the directory two levels up from the used cache path to find all cache files
        all_caches = list(scan_directory(used_cache_path.parents[1]))

        # Determine unused cache paths by subtracting the used cache path from all cache paths
        unused_cache_paths = {Path(cache) for cache in all_caches} - {
            used_cache_path
        }

        # Extract and sort all versions from the cache paths
        all_versions = sorted(
            set(self._extract_version(Path(p)) for p in all_caches)
        )
        latest_version = max(all_versions)
        current_version = self._extract_version(used_cache_path)

        # Create dictionaries for used and unused cache versions
        used_cache_version = {used_cache_path: current_version}
        unused_cache_versions = {
            path: self._extract_version(path) for path in unused_cache_paths
        }
        is_current_latest = latest_version == current_version

        # Sort unused cache versions in descending order
        sorted_unused_cache_versions = dict(
            sorted(
                unused_cache_versions.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

        # Update cache_data with the final values
        cache_data.update(
            {
                "used_cache_path": used_cache_version,
                "unused_cache_paths": sorted_unused_cache_versions,
                "latest_version": latest_version,
                "current_version": current_version,
                "all_versions": all_versions,
                "is_current_latest": is_current_latest,
                "valid_cache_path": True,
            }
        )

        return cache_data.get_data()
