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
   * [Settings](#settings)
   * [Advanced](#advanced)
   * [Contact](#contact)
<!--te-->



<!-- INSTALLATION -->
## Installation

To install, simply copy-paste the [package.json](houdini/packages/fxhoucachemanager.json) file inside your `$HOUDINI_USER_PREF_DIR/packages` folder, and replace the value of the `$FXHOUCACHEMANAGER` path depending on your OS.



<!-- HOW-TO-USE -->
## How-to Use

You can launch the **FX Cache Manager** through the **FX** menu, or the **FX Cache Manager** shelf tool inside the **FX** shelf.

You will be presented with this UI:

<p align="center">
  <img width="500" src="docs/images/houdini_YfAwyT33tU.png">
</p>

<p align="center">
  <img width="500" src="docs/images/___">
</p>

The tool will scan for caches in the root folder you've set in the [settings](#settings).
The caches should be following this format `<cache_root>/<cache_name>/<cache_version>/<cache_name>.<ext>`, e.g. `$HIP/geo/flip/v001/flip.bgeo.sc`.

You can filter the caches by name, but also by extensions using the buttons on the bottom right of the UI.

<p align="center">
  <img width="500" src="docs/images/houdini_9IohqVM41N.png">
</p>

You can use the dropdown menu to select the version you want to load. It will immediately load the cache in the scene.

<p align="center">
  <img width="500" src="docs/images/houdini_tGH3eV90WE.png">
</p>

<p align="center">
  <img width="500" src="docs/images/houdini_RXORyu4roH.png">
</p>

You can expand the parent item to see all the versions available for a cache. The parent item will display the version currently loaded in the scene, and the children items will display the other versions available. The highest found version will be displayed in green, outdated versions will be displayed in yellow.

If a path is referenced but not found on disk, the version will be displayed in red. If the file exists on disk but doesn't follow the expected format, the version will be displayed in grey-blue.

<p align="center">
  <img width="500" src="docs/images/houdini_ll3phiJd8y.png">
</p>

A right-click on a selection of caches will open a context menu allowing you to perform a variety of actions:

<p align="center">
  <img width="500" src="docs/images/houdini_VBsgukKjOg.png">
</p>

When selecting **Update All to Latest** or **Delete Unused Caches**, a confirmation dialog will appear, asking you to confirm the action.

<p align="center">
  <img width="400" src="docs/images/houdini_0ffjQeKfN9.png">
</p>

<p align="center">
  <img width="400" src="docs/images/houdini_CADX3jVyfA.png">
</p>

<!-- SETTINGS -->
## Settings

You can modify the settings of the tool by clicking on the **Edit** > **Settings** button, in the menu bar.
A dialog will appear, allowing you to set the regex pattern to use for the version extraction, the Houdini environment variable to use when looking for all the referenced files, and the root folder to scan for caches.

<p align="center">
  <img width="300" src="docs/images/houdini_Dhuz8CAFiY.png">
</p>


You can also set the logger verbosity level in the **Edit** > **Log Level** menu.



<!-- ADVANCED -->
## Advanced

The log and configuration files are stored in the `%APPDATA%/fxhoucachemanager` folder on Windows, and in the `$HOME/.fxhoucachemanager` folder on Linux and macOS.


<!-- CONTACT -->
## Contact

Project Link: [fxgui](https://github.com/healkeiser/fxhoucachemanager)

<p align='center'>
  <!-- GitHub profile -->
  <a href="https://github.com/healkeiser">
    <img src="https://img.shields.io/badge/healkeiser-181717?logo=github&style=social" alt="GitHub"/></a>&nbsp;&nbsp;
  <!-- LinkedIn -->
  <a href="https://www.linkedin.com/in/valentin-beaumont">
    <img src="https://img.shields.io/badge/Valentin%20Beaumont-0A66C2?logo=linkedin&style=social" alt="LinkedIn"/></a>&nbsp;&nbsp;
  <!-- Behance -->
  <a href="https://www.behance.net/el1ven">
    <img src="https://img.shields.io/badge/el1ven-1769FF?logo=behance&style=social" alt="Behance"/></a>&nbsp;&nbsp;
  <!-- X -->
  <a href="https://twitter.com/valentinbeaumon">
    <img src="https://img.shields.io/badge/@valentinbeaumon-1DA1F2?logo=x&style=social" alt="Twitter"/></a>&nbsp;&nbsp;
  <!-- Instagram -->
  <a href="https://www.instagram.com/val.beaumontart">
    <img src="https://img.shields.io/badge/@val.beaumontart-E4405F?logo=instagram&style=social" alt="Instagram"/></a>&nbsp;&nbsp;
  <!-- Gumroad -->
  <a href="https://healkeiser.gumroad.com/subscribe">
    <img src="https://img.shields.io/badge/healkeiser-36a9ae?logo=gumroad&style=social" alt="Gumroad"/></a>&nbsp;&nbsp;
  <!-- Gmail -->
  <a href="mailto:valentin.onze@gmail.com">
    <img src="https://img.shields.io/badge/valentin.onze@gmail.com-D14836?logo=gmail&style=social" alt="Email"/></a>&nbsp;&nbsp;
  <!-- Buy me a coffee -->
  <a href="https://www.buymeacoffee.com/healkeiser">
    <img src="https://img.shields.io/badge/Buy Me A Coffee-FFDD00?&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me A Coffee"/></a>&nbsp;&nbsp;
</p>