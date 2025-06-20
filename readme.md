<div align="center">

# 🎮 GOG Mod Manager (GMM)

**Steam Workshop mod installer for non-steam games (People Playground & Project Zomboid).**

[![Downloads](https://img.shields.io/github/downloads/NotClavilux/PyPPGModManager/total.svg)](https://github.com/NotClavilux/PyPPGModManager/releases)
[![Version](https://img.shields.io/github/v/release/NotClavilux/PyPPGModManager)](https://github.com/NotClavilux/PyPPGModManager/releases)
[![License](https://img.shields.io/github/license/NotClavilux/PyPPGModManager)](https://github.com/NotClavilux/PyPPGModManager/blob/main/LICENSE)

[Download](https://github.com/NotClavilux/PyPPGModManager/releases) • [Features](#what-it-does) • [Installation](#installing) • [Usage](#usage)

![image](https://github.com/user-attachments/assets/a3aff44b-f1fe-4628-bb74-4b1c96165186)

</div>

**GOG Mod Manager** is a bridge between the Steam Workshop and non-steam installations of games that allows you to install Steam Workshop mods. It's an experimental branch of the PyPPG Mod Manager, now supporting both People Playground and Project Zomboid, with more games planned for the future. Written in Python with a browser userscript for seamless mod management directly from Steam Workshop pages.

---

## What it does

- **Multi-Game Support:** Currently supports People Playground and Project Zomboid, with more games planned.
- **Simple Mod Installation:** Install mods directly from their Steam Workshop pages with a single click.
- **Browser Integration:** A userscript allows you to manage mods directly from their Steam Workshop mod page.
- **Checks Updates:** For individual mods or all installed mods.
- **Enable/Disable Any Mod:** Easily toggle mods on or off by moving them to a disabled folder.
- **Lightweight:** No unnecessary bloat, just mod management.
- **Cross-Platform:** Works on Windows, Linux, and macOS.
- **Game-Specific Configuration:** Each game has its own configuration and mod folder structure.

## Installing

### Prerequisites

1. **Python:** Version 3.7+ is recommended.
2. **Userscript Manager:** Like [Tampermonkey](https://www.tampermonkey.net/) or [Violentmonkey](https://violentmonkey.github.io/).
3. **Supported Games:** People Playground and/or Project Zomboid.

### 1. Python Server

1. Download the `gmm.py` script from the [Releases page](https://github.com/NotClavilux/PyPPGModManager/releases) or clone this repository.
2. Open a terminal or command prompt and run:

   ```bash
   pip install requests
   ```

### 2. Userscript

1. Install one of [Tampermonkey](https://www.tampermonkey.net/), [Violentmonkey](https://violentmonkey.github.io/), etc (Userscript Manager).
2. Install the userscript from [here](https://raw.githubusercontent.com/NotClavilux/PyPPGModManager/refs/heads/main/ppg.user.js) (will be updated to gmm.user.js in future releases).

## Usage

> When running for the first time, you will be prompted to select which game to configure (People Playground or Project Zomboid), the game directory, and where to save the helper SteamCMD tool.

1. **Python script:** Make sure that the `gmm.py` Python script is running.
   To run the script, open a command prompt and navigate to where you saved `gmm.py` and run:

   ```bash
   python gmm.py
   ```

2. **Open Steam Workshop:** Open a mod page for either People Playground or Project Zomboid on the Steam Workshop.
3. The userscript will add a set of buttons:
   - **Install Mod** (if the mod isn't installed)
   - **Update Mod** (if available)
   - **Delete Mod**
   - **Enable/Disable Mod**
4. **Check for Updates:** (on bottom-right) this button scans all your mods for updates.

Now you can launch the game and all your enabled mods should be active. You only need to run the python script when you want to install or manage mods.

### Project Zomboid Specific Features

For Project Zomboid:
- Mods are extracted directly to the game's root directory since mod archives already contain the proper folder structure
- The folder picker UI makes it easy to select your game directory on any platform
- When disabling mods, they're moved to a `disabled_mods` folder in your game directory

## Roadmap

- **More Games Support:** Add support for additional non-Steam games that use Steam Workshop.
- **Global Configuration:** Centralized configuration for managing multiple games.
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

This project is meant for users who legitimately own the games (People Playground, Project Zomboid, etc.) but aren't using the Steam version.
We do not support piracy. Please support the developers and buy the games legally.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/NotClavilux/PyPPGModManager/blob/main/LICENSE) file for details.

---

<div align="center">

_"Modding should be effortless, for any game."_
**Made with ❤️ by NotClavilux**

</div>
