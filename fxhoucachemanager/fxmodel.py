"""Model part for the FX Cache Manager tool."""

# Built-in
from collections import defaultdict
import os
import re
import logging
from pathlib import Path
import time
from typing import Generator, List, Union

# Third-party
import hou
from qtpy.QtCore import QObject, Signal

# Internal
from fxhoucachemanager import fxview, fxsettings
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

    def update(self, updates):
        self.data.update(updates)

    def get_data(self):
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
        self.houdini_variable = houdini_variable
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
        file_references = hou.fileReferences(self.houdini_variable, True)
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

            # Example dictionary:
            # {
            #     "node_name": {
            #         "cache_node": hou.Node,
            #         "cache_path": Path,
            #     },

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

        self.finished.emit(caches)

    def _filter_file_references(self, file_references: List) -> List:
        """Filter and sort file references to remove duplicates."""

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

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("Number files referenced: %d", len(file_references))
            _logger.debug(
                "Number filtered files referenced: %d",
                len(filtered_file_references),
            )

            for reference in file_references:
                _logger.debug("File reference: %s", reference)

            for reference in filtered_file_references:
                _logger.debug("Filtered file reference: %s", reference)

        return filtered_file_references

    def _build_cache_data(
        self, referenced_parm: hou.Parm, used_cache_path: Path
    ):
        """Build cache data for a single file reference."""

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
