<div align="center">

# 🎮 PyPPG Mod Manager

**Steam Workshop mod installer for non-steam People Playground.**

[![Downloads](https://img.shields.io/github/downloads/NotClavilux/PyPPGModManager/total.svg)](https://github.com/NotClavilux/PyPPGModManager/releases)
[![Version](https://img.shields.io/github/v/release/NotClavilux/PyPPGModManager)](https://github.com/NotClavilux/PyPPGModManager/releases)
[![License](https://img.shields.io/github/license/NotClavilux/PyPPGModManager)](https://github.com/NotClavilux/PyPPGModManager/blob/main/LICENSE)

[Download](https://github.com/NotClavilux/PyPPGModManager/releases) • [Features](#what-it-does) • [Installation](#installing) • [Usage](#usage)

![image](https://github.com/user-attachments/assets/a3aff44b-f1fe-4628-bb74-4b1c96165186)

</div>

**PyPPG Mod Manager** is a bridge between the Steam Workshop and a non-steam installation of _People Playground_ that allows you to install Steam Workshop mods to the game. Its written in python and has a browser userscript to allow mod management for the game from Steam Workshop itself.

---

## What it does

- **Simple Mod Installation:** Install mods directly from their Steam Workshop pages with a single click.
- **Browser Integration:** A userscript allows you to manage mods directly from their Steam Workshop mod page.
- **Checks Updates:** For individual mods or all installed mods.
- **Enable/Disable Any Mod:** Easily toggle mods on or off without having to open people playground.
- **Lightweight:** No unnecessary bloat, just mod management.
- **Cross-Platform:** Works on Windows, Linux, and macOS.

## Installing

### Prerequisites

1. **Python:** Version 3.7+ is recommended.
2. **Userscript Manager:** Like [Tampermonkey](https://www.tampermonkey.net/) or [Violentmonkey](https://violentmonkey.github.io/).
3. **People Playground:** You need the game, obviously.

### 1. Python Server

1. Download the `ppg.py` script from the [Releases page](https://github.com/NotClavilux/PyPPGModManager/releases) or clone this repository.
2. Open a terminal or command prompt and run:

   ```bash
   pip install requests
   ```

### 2. Userscript

1. Install one of [Tampermonkey](https://www.tampermonkey.net/), [Violentmonkey](https://violentmonkey.github.io/), etc (Userscript Manager).
2. Install the userscript from [here](https://raw.githubusercontent.com/NotClavilux/PyPPGModManager/refs/heads/main/ppg.user.js).

## Usage

> When running for the first time, you will be prompted for the People Playground game directory and where to save the helper SteamCMD tool.

1. **Python script:** Make sure that the `ppg.py` Python script is running.
   To run the script, open a command prompt and navigate to where you saved `ppg.py` and run:

   ```bash
   python ppg.py
   ```

2. **Open Steam Workshop:** Open the People Playground mod page on the Steam Workshop.
3. The userscript will add a set of buttons:
   - **Install to PyPPG** (if the mod isn't installed)
   - **Update Mod** (if available)
   - **Delete Mod**
   - **Enable/Disable Mod**
4. **Check for Updates:** (on bottom-right) this button scans all your mods for updates.

Now you can launch the game and all your enabled mods should be active in People Playground. You only need to run the python script when you want to install mods.

## Roadmap

- **Dedicated Mod Manager UI:** A dedicated web interface or simple desktop app for managing your mods, without needing to open a Steam page.
- **Batch Operations:** Install, update, or delete multiple mods at once (e.g., from a Steam Collection).
- **Mod Profiles:** Create and switch between different sets of mods.
- **Settings Management:** Better way to update game/SteamCMD paths after initial setup.
- **Backup:** Option to backup mod lists.

## Contributing

Contributions are welcome! Whether it's reporting a bug, suggesting a feature, or submitting a pull request, your help is appreciated.

- Open an issue and describe any bugs or problems you encounter.
- Share your ideas for new functionality or improvements.
- Feel free to fork the repository and submit PRs for bug fixes or new features.

## Disclaimer

This project is meant for users who legitimately own People Playground but aren't using the Steam version.
We do not support piracy. Please support the devs and buy the game legally.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/NotClavilux/PyPPGModManager/blob/main/LICENSE) file for details.

---

<div align="center">

_"Modding should be effortless."_
**Made with ❤️ by NotClavilux**

</div>
