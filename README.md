<div align="center">

  ![Logo](https://raw.githubusercontent.com/healkeiser/fxhoucachemanager/main/fxhoucachemanager/images/icons/fxhoucachemanager_dark.svg#gh-light-mode-only)
  ![Logo](https://raw.githubusercontent.com/healkeiser/fxhoucachemanager/main/fxhoucachemanager/images/icons/fxhoucachemanager_light.svg#gh-dark-mode-only)

  <h3 align="center">fxcachemanager</h3>

  <p align="center">
    Cache manager for Houdini.
    <br/><br/>
  </p>

  ##

  <p align="center">
    <!-- Maintenance status -->
    <img src="https://img.shields.io/badge/maintenance-actively--developed-brightgreen.svg?&label=Maintenance">&nbsp;&nbsp;
    <!-- <img src="https://img.shields.io/badge/maintenance-deprecated-red.svg?&label=Maintenance">&nbsp;&nbsp; -->
    <!-- License -->
    <img src="https://img.shields.io/badge/License-MIT-brightgreen.svg?&logo=open-source-initiative&logoColor=white" alt="License: MIT"/>&nbsp;&nbsp;
    <!-- Last Commit -->
    <img src="https://img.shields.io/github/last-commit/healkeiser/fxhoucachemanager?logo=github&label=Last%20Commit" alt="Last Commit"/>&nbsp;&nbsp;
    <!-- Commit Activity -->
    <a href="https://github.com/healkeiser/fxhoucachemanager/pulse" alt="Activity">
      <img src="https://img.shields.io/github/commit-activity/m/healkeiser/fxhoucachemanager?&logo=github&label=Commit%20Activity"/></a>&nbsp;&nbsp;
    <!-- GitHub stars -->
    <img src="https://img.shields.io/github/stars/healkeiser/fxhoucachemanager" alt="GitHub Stars"/>&nbsp;&nbsp;
  </p>

</div>



<!-- TABLE OF CONTENTS -->
## Table of Contents
<!--ts-->
   * [Installation](#installation)
   * [How-to Use](#how-to-use)
   * [Advanced](#advanced)
<!--te-->



<!-- INSTALLATION -->
## Installation

To install, simply copy-paste the [package.json](houdini/packages/fxhoucachemanager.json) file inside your `$HOUDINI_USER_PREF_DIR/packages` folder, and replace the value of the `$FXHOUCACHEMANAGER_ROOT` path depending on your OS.

You'll also need an access to the `qtpy` package, which is added in the same file through `$PYTHONPATH`: modify the path depending on your Python version, after installing the package using pip: `python -m pip install qtpy`.



<!-- HOW-TO-USE -->
## How-to Use

You can launch the **FX Cache Manager** through the **FX** menu, or the **FX Cache Manager** shelf tool inside the **FX** shelf.

