<div align="center">

# 🎮 PyPPG Mod Manager

**Bridging the gap between non-steam People Playground and steam workshop.**

[![Downloads](https://img.shields.io/github/downloads/NotClavilux/PyPPGModManager/total.svg)](https://github.com/NotClavilux/PyPPGModManager/releases)
[![Version](https://img.shields.io/github/v/release/NotClavilux/PyPPGModManager)](https://github.com/NotClavilux/PyPPGModManager/releases)
[![License](https://img.shields.io/github/license/NotClavilux/PyPPGModManager)](https://github.com/NotClavilux/PyPPGModManager/blob/main/LICENSE)

[Download Latest Release](https://github.com/NotClavilux/PyPPGModManager/releases) • [Features](#features) • [Setup](#setup) • [Usage](#usage) • [Roadmap](#roadmap) • [Contributing](#contributing)

</div>

---

## Overview

**PyPPG Mod Manager** is a tool designed to simplify managing Steam Workshop mods for *People Playground*. It combines a Python backend with a browser userscript to integrate mod management directly into your Steam Workshop browsing experience. It's built to be fast, minimal, and effective.

> **Note:** This tool is intended for users who legally own People Playground. While it can be particularly helpful for non-Steam versions, it works for any version by managing mods in a local directory.

---

## Features

-   **One-Click Steam Workshop Installs:** Install mods directly from their Steam Workshop pages.
-   **Browser Integration:** A Tampermonkey userscript adds Install/Update/Delete/Enable/Disable buttons to People Playground mod pages.
-   **Mod Updates:** Check for updates for individual mods or all installed mods.
-   **Enable/Disable Mods:** Easily toggle mods on or off without having to open people playground.
-   **Clean Setup:** Configure your game and SteamCMD paths once.
-   **Lightweight & Focused:** No unnecessary bloat, just core mod management.
-   **Cross-Platform:** Python backend works on Windows, Linux, and macOS.

---

## Setup

### Prerequisites

1.  **Python:** Version 3.7+ is recommended.
2.  **Tampermonkey:** A browser extension for managing userscripts (available for Chrome, Firefox, Edge, Opera, etc.).
3.  **People Playground:** The game itself.

### 1. Python Backend

1.  **Download:** Get the latest `ppg.py` script from the [Releases page](https://github.com/NotClavilux/PyPPGModManager/releases) or clone the repository.
2.  **Install Dependencies:** Open a terminal or command prompt, navigate to the folder where you saved `ppg.py`, and run:
    ```bash
    pip install requests
    ```
3.  **Run Backend:** Execute the script:
    ```bash
    python ppg.py
    ```
    *   On the first run, you'll be guided through a setup to specify your People Playground game directory and a location for SteamCMD (a tool for downloading workshop items).
    *   The backend server will start on `http://localhost:8000`. Keep this terminal window running while using the mod manager.

### 2. Browser Userscript (Tampermonkey)

1.  **Install Tampermonkey:** Add the Tampermonkey extension to your preferred browser if you haven't already.
2.  **Create New Script:** Open the Tampermonkey dashboard and click "Create a new script."
3.  **Add PyPPG Script:**
    *   Delete any default content in the new script editor.
    *   Copy the entire content of the PyPPG Mod Manager userscript (`pyppg_userscript.js` from the release or repository).
    *   Paste it into the Tampermonkey editor.
    *   Save the script (usually File > Save or Ctrl+S). Tampermonkey will automatically enable it.

---

## Usage

1.  **Start Backend:** Ensure the `ppg.py` Python script is running.
2.  **Open Steam Workshop:** Navigate to a People Playground mod page on the Steam Workshop.
3.  **Use Integrated Buttons:** The userscript will add a set of buttons:
    *   **Install to PyPPG:** If the mod isn't installed.
    *   **Update Mod:** If an update is available.
    *   **Delete Mod / Delete Mod (Disabled):** To remove the mod.
    *   **Enable Mod / Disable Mod:** To toggle the mod's active state.
4.  **Global Update Check:** A "Check All PyPPG Updates" button will appear (usually bottom-right) on workshop pages to scan all your mods.
5.  **Launch Game:** Your managed mods should now be active (if enabled) in People Playground.

---

## Roadmap (Future Enhancements)

*   **Dedicated Mod Manager UI:** A web interface or simple desktop app for viewing and managing all installed mods, changing settings, etc., without needing to be on a Steam page.
*   **Batch Operations:** Allow installing, updating, or deleting multiple mods at once (e.g., from a Steam Collection).
*   **Mod Profiles:** Create and switch between different sets of enabled mods easily.
*   **Other games:** Support for more games?
*   **Settings Management:** An easier way to update game/SteamCMD paths after initial setup.
*   **Backup & Restore:** Option to backup mod lists or configurations.

---

## Contributing

Contributions are welcome! Whether it's reporting a bug, suggesting a feature, or submitting a pull request, your help is appreciated.

-   **Report Issues:** Open an issue to describe any bugs or problems you encounter.
-   **Suggest Features:** Share your ideas for new functionality or improvements.
-   **Pull Requests:** Feel free to fork the repository and submit PRs for bug fixes or new features.

---

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/NotClavilux/PyPPGModManager/blob/main/LICENSE) file for details.

---

<div align="center">

*"Modding should be effortless."*
**Made with ❤️ by NotClavilux**
**Thanks to ChatGPT for helping with the readme.**

</div>
