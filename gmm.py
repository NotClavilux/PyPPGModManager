import os
import sys
import json
import subprocess
import platform
import time
import re
import shutil
import logging
import tempfile
import zipfile
import requests
import tkinter as tk
from tkinter import filedialog
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from logging.handlers import RotatingFileHandler

GAME_CONFIGS = {
    "ppg": {
        "name": "People Playground",
        "app_id": "1118200",
        "mods_folder": "Mods",
        "exe_names": {
            "windows": "People Playground.exe",
        }
    },
    "pz": {
        "name": "Project Zomboid",
        "app_id": "108600",
        "mods_folder": "mods",
        "exe_names": {
            "windows": "ProjectZomboid.exe",
            "linux": "ProjectZomboid",
        }
    }
}

MOD_INFO_FILE = "modinfo.json"
DISABLED_MODS_FOLDER = "disabled_mods"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('ppg_mod_manager.log', maxBytes=5*1024*1024, backupCount=2),
        logging.StreamHandler(sys.stdout)
    ]
)

class ModManagerConfig:
    def __init__(self):
        self.games = {}
        self.active_game = None
        self.steamcmd_dir = ""
        self.steamcmd_exe_name = "steamcmd.exe" if platform.system() == "Windows" else "steamcmd.sh"
        self.config_file_path = self._get_config_path()
        self.load_config()

    def _get_config_path(self):
        if platform.system() == "Windows":
            config_dir = os.path.join(os.getenv('APPDATA', os.path.expanduser("~")), 'GOGModManager')
        else:
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'GOGModManager')

        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    def load_config(self):
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    data = json.load(f)

                self.games = data.get("games", {})
                self.active_game = data.get("active_game")
                self.steamcmd_dir = data.get("steamcmd_dir", "")

                if (self.games and self.active_game in self.games and
                    self.steamcmd_dir and os.path.isfile(os.path.join(self.steamcmd_dir, self.steamcmd_exe_name))):
                    for game_key, game_data in self.games.items():
                        game_dir = game_data.get("game_dir")
                        if game_dir and os.path.isdir(game_dir):
                            game_config = GAME_CONFIGS.get(game_key)
                            if game_config:
                                mods_folder = game_config["mods_folder"]
                                mods_dir = os.path.join(game_dir, mods_folder)
                                os.makedirs(mods_dir, exist_ok=True)

                                disabled_mods_dir = os.path.join(game_dir, DISABLED_MODS_FOLDER)
                                os.makedirs(disabled_mods_dir, exist_ok=True)

                                if game_key == "ppg":
                                    contraptions_dir = os.path.join(game_dir, "Contraptions")
                                    os.makedirs(contraptions_dir, exist_ok=True)

                    logging.info(f"Config loaded successfully")
                    return
            except Exception as e:
                logging.error(f"Error loading config: {e}")

        self.setup_new_config()

    def setup_new_config(self):
        logging.info("Setting up new configuration")
        print("Available games:")
        for key, game in GAME_CONFIGS.items():
            print(f"- {key}: {game['name']}")

        game_key = ""
        while game_key not in GAME_CONFIGS:
            game_key = input("Select game to configure (e.g., ppg, pz): ").strip().lower()
            if game_key not in GAME_CONFIGS:
                print(f"Invalid game selection. Please choose from: {', '.join(GAME_CONFIGS.keys())}")

        game_config = GAME_CONFIGS[game_key]
        system = platform.system().lower()
        exe_name = game_config["exe_names"].get(system, "")

        game_dir = ""
        
        print(f"Please select your {game_config['name']} directory in the file dialog...")
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        while True:
            game_dir = filedialog.askdirectory(title=f"Select {game_config['name']} Directory")
            
            if not game_dir:
                print("No directory selected. Please try again.")
                continue
                
            game_exe = os.path.join(game_dir, exe_name)
            
            if os.path.isdir(game_dir) and os.path.exists(game_exe):
                break
            else:
                print(f"Invalid {game_config['name']} directory. Please try again.")

        if not self.games:
            self.games = {}

        self.games[game_key] = {
            "game_dir": game_dir,
            "app_id": game_config["app_id"]
        }

        self.active_game = game_key

        mods_dir = os.path.join(game_dir, game_config["mods_folder"])
        os.makedirs(mods_dir, exist_ok=True)

        disabled_mods_dir = os.path.join(game_dir, DISABLED_MODS_FOLDER)
        os.makedirs(disabled_mods_dir, exist_ok=True)

        if game_key == "ppg":
            contraptions_dir = os.path.join(game_dir, "Contraptions")
            os.makedirs(contraptions_dir, exist_ok=True)

        default_dir = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), 'GOGModManager', 'SteamCMD')
        print(f"Please select SteamCMD directory (or cancel to use default: {default_dir})")
        
        steamcmd_dir = filedialog.askdirectory(title=f"Select SteamCMD Directory (Cancel for default)")
        self.steamcmd_dir = steamcmd_dir if steamcmd_dir else default_dir
        os.makedirs(self.steamcmd_dir, exist_ok=True)

        steamcmd_path = os.path.join(self.steamcmd_dir, self.steamcmd_exe_name)
        if not os.path.isfile(steamcmd_path):
            if input("Download SteamCMD? (yes/no): ").lower() == 'yes':
                self.download_steamcmd()
            else:
                print("SteamCMD is required. Exiting.")
                sys.exit(1)

        self.save_config()

    def get_game_dir(self, game_key=None):
        if not game_key:
            game_key = self.active_game

        if game_key in self.games:
            return self.games[game_key].get("game_dir", "")
        return ""

    def get_mods_dir(self, game_key=None):
        if not game_key:
            game_key = self.active_game

        if game_key in self.games and game_key in GAME_CONFIGS:
            game_dir = self.games[game_key].get("game_dir", "")
            mods_folder = GAME_CONFIGS[game_key]["mods_folder"]
            return os.path.join(game_dir, mods_folder)
        return ""

    def get_disabled_mods_dir(self, game_key=None):
        if not game_key:
            game_key = self.active_game

        if game_key in self.games:
            game_dir = self.games[game_key].get("game_dir", "")
            return os.path.join(game_dir, DISABLED_MODS_FOLDER)
        return ""

    def get_contraptions_dir(self):
        if self.active_game == "ppg":
            game_dir = self.get_game_dir()
            return os.path.join(game_dir, "Contraptions")
        return ""

    def get_app_id(self, game_key=None):
        if not game_key:
            game_key = self.active_game

        if game_key in self.games:
            return self.games[game_key].get("app_id", "")
        elif game_key in GAME_CONFIGS:
            return GAME_CONFIGS[game_key]["app_id"]
        return ""

    def save_config(self):
        config_data = {
            "games": self.games,
            "active_game": self.active_game,
            "steamcmd_dir": self.steamcmd_dir
        }
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            logging.info(f"Configuration saved")
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")

    def download_steamcmd(self):
        logging.info(f"Downloading SteamCMD")
        os.makedirs(self.steamcmd_dir, exist_ok=True)

        system = platform.system()
        if system == "Windows":
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            archive_name = "steamcmd.zip"
        elif system == "Linux":
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
            archive_name = "steamcmd_linux.tar.gz"
        elif system == "Darwin":
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_osx.tar.gz"
            archive_name = "steamcmd_osx.tar.gz"
        else:
            logging.error(f"Unsupported OS: {system}")
            return

        try:
            archive_path = os.path.join(self.steamcmd_dir, archive_name)
            response = requests.get(url, stream=True)
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            shutil.unpack_archive(archive_path, self.steamcmd_dir)
            os.remove(archive_path)

            if system != "Windows":
                steamcmd_sh = os.path.join(self.steamcmd_dir, "steamcmd.sh")
                if os.path.isfile(steamcmd_sh):
                    os.chmod(steamcmd_sh, 0o755)

            logging.info("SteamCMD downloaded and extracted")
        except Exception as e:
            logging.error(f"Error downloading SteamCMD: {e}")

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else "Untitled Mod"

def get_mod_details_from_steam(mod_id):
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = {'itemcount': 1, 'publishedfileids[0]': mod_id}

    try:
        response = requests.post(url, data=data)
        data = response.json()
        if data['response']['result'] == 1:
            details = data['response']['publishedfiledetails'][0]
            tags = []
            if 'tags' in details:
                tags = [tag.get('tag', '').strip() for tag in details['tags']]

            return {
                "mod_id": details['publishedfileid'],
                "time_updated": details.get('time_updated', 0),
                "title": details.get('title', f'Mod {mod_id}'),
                "tags": tags
            }
    except Exception as e:
        logging.error(f"Error getting mod details: {e}")

    return None

def download_mod_via_ggnetwork(mod_id, target_dir):
    logging.info(f"Downloading mod {mod_id} via GGNetwork")

    try:
        api_url = "https://api.ggntw.com/steam.request"
        payload = {"url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"}
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://ggntw.com',
            'Referer': 'https://ggntw.com/'
        }

        response = requests.post(api_url, json=payload, headers=headers)
        data = response.json()

        if data.get("result") == 1 and "url" in data:
            cdn_url = data["url"]
            temp_zip = os.path.join(tempfile.gettempdir(), f"gmm_{mod_id}.zip")

            with requests.get(cdn_url, stream=True) as r:
                with open(temp_zip, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(target_dir)

            os.remove(temp_zip)
            return True, target_dir, "Success"
        else:
            return False, None, data.get("error_msg", "Unknown error")

    except Exception as e:
        logging.error(f"GGNetwork download error: {e}")
        return False, None, str(e)


class ModManagerHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format_str, *args):
        logging.info(f"{self.address_string()} - {format_str % args}")

    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _find_mod_path(self, mod_id):
        mods_dir = config.get_mods_dir()
        disabled_mods_dir = config.get_disabled_mods_dir()
        directories = [mods_dir]

        if config.active_game == "ppg":
            contraptions_dir = config.get_contraptions_dir()
            if contraptions_dir:
                directories.append(contraptions_dir)

        if disabled_mods_dir:
            directories.append(disabled_mods_dir)

        for directory in directories:
            if not os.path.isdir(directory):
                continue

            for folder_name in os.listdir(directory):
                mod_path = os.path.join(directory, folder_name)
                if not os.path.isdir(mod_path):
                    continue

                info_file = os.path.join(mod_path, MOD_INFO_FILE)
                if os.path.isfile(info_file):
                    try:
                        with open(info_file, 'r') as f:
                            info = json.load(f)
                        if str(info.get("mod_id")) == str(mod_id):
                            if directory == disabled_mods_dir:
                                info["enabled"] = False
                            return mod_path, info
                    except:
                        pass

        return None, None

    def _read_mod_info(self, mod_path):
        info_file = os.path.join(mod_path, MOD_INFO_FILE)
        if os.path.isfile(info_file):
            try:
                with open(info_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _write_mod_info(self, mod_path, info):
        info_file = os.path.join(mod_path, MOD_INFO_FILE)
        try:
            with open(info_file, 'w') as f:
                json.dump(info, f, indent=4)
            return True
        except:
            return False

    def do_GET(self):
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        mod_id = query.get('id', [None])[0]
        path = parsed_url.path

        try:
            if path == '/status':
                self._send_response(200, {"status": "online", "version": "1.5.0"})

            elif path == '/is_installed':
                if not mod_id:
                    self._send_response(400, {"error": "Missing mod ID"})
                    return

                mod_path, mod_info = self._find_mod_path(mod_id)
                if mod_path and mod_info:
                    self._send_response(200, {
                        "mod_id": mod_id,
                        "installed": True,
                        "enabled": mod_info.get("enabled", True),
                        "title": mod_info.get("title", "Unknown"),
                        "is_contraption": mod_info.get("is_contraption", False)
                    })
                else:
                    self._send_response(200, {"mod_id": mod_id, "installed": False})

            elif path == '/install':
                if not mod_id:
                    self._send_response(400, {"error": "Missing mod ID"})
                    return

                success, message = self._install_mod(mod_id)
                self._send_response(200, {"success": success, "message": message})

            elif path == '/delete':
                if not mod_id:
                    self._send_response(400, {"error": "Missing mod ID"})
                    return

                success, message = self._delete_mod(mod_id)
                self._send_response(200, {"success": success, "message": message})

            elif path == '/check_update':
                if not mod_id:
                    self._send_response(400, {"error": "Missing mod ID"})
                    return

                response = self._check_mod_update(mod_id)
                self._send_response(200, response)

            elif path == '/check_updates':
                results = self._check_all_mod_updates()
                self._send_response(200, {"success": True, "data": results})

            elif path == '/toggle_mod_enabled':
                if not mod_id:
                    self._send_response(400, {"error": "Missing mod ID"})
                    return

                enable = query.get('enable', ['true'])[0].lower() == 'true'
                success, message = self._toggle_mod(mod_id, enable)
                self._send_response(200, {"success": success, "message": message})

            else:
                self._send_response(404, {"error": "Endpoint not found"})

        except Exception as e:
            logging.error(f"Error handling request: {e}")
            self._send_response(500, {"error": f"Server error: {e}"})

    def _install_mod(self, mod_id):
        temp_dir = None
        success, download_path, message = self._download_with_steamcmd(mod_id)

        if not success:
            logging.info(f"SteamCMD failed, trying GGNetwork")
            temp_dir = tempfile.mkdtemp(prefix=f"gmm_mod_{mod_id}_")
            success, download_path, message = download_mod_via_ggnetwork(mod_id, temp_dir)

        if not success or not download_path:
            return False, f"Failed to download mod: {message}"

        steam_details = get_mod_details_from_steam(mod_id)
        title = steam_details.get("title", f"Mod {mod_id}") if steam_details else f"Mod {mod_id}"

        is_contraption = False
        if config.active_game == "ppg" and steam_details and "tags" in steam_details:
            is_contraption = any(tag.lower() == "contraptions" for tag in steam_details["tags"])

        safe_title = sanitize_filename(title)
        mod_dirname = f"{safe_title} [{mod_id}]"
        
        mod_final_path = None
        game_dir = config.get_game_dir()
        
        if config.active_game == "pz":
            mod_final_path = game_dir
            
            old_path, old_info = self._find_mod_path(mod_id)
            if old_path:
                try:
                    if old_info and "folder_name" in old_info:
                        old_mod_path = os.path.join(config.get_mods_dir(), old_info["folder_name"])
                        if os.path.exists(old_mod_path):
                            shutil.rmtree(old_mod_path)
                except Exception as e:
                    logging.error(f"Error removing old mod: {e}")
            
            try:
                for item in os.listdir(download_path):
                    src_path = os.path.join(download_path, item)
                    if os.path.isdir(src_path) and item.lower() == "mods":
                        for mod_folder in os.listdir(src_path):
                            mod_src = os.path.join(src_path, mod_folder)
                            mod_dest = os.path.join(game_dir, "mods", mod_folder)
                            if os.path.exists(mod_dest):
                                shutil.rmtree(mod_dest)
                            shutil.copytree(mod_src, mod_dest)
                            
                            mod_info_path = os.path.join(mod_dest, MOD_INFO_FILE)
                            mod_info = {
                                "mod_id": mod_id,
                                "title": title,
                                "folder_name": mod_folder,
                                "steam_time_updated": steam_details.get("time_updated", 0) if steam_details else 0,
                                "local_install_time": int(time.time()),
                                "enabled": True,
                                "is_contraption": False
                            }
                            with open(mod_info_path, 'w') as f:
                                json.dump(mod_info, f, indent=4)
            except Exception as e:
                return False, f"Failed to install Project Zomboid mod: {e}"
                
        else:
            if is_contraption and config.active_game == "ppg":
                mod_final_path = os.path.join(config.get_contraptions_dir(), mod_dirname)
            else:
                mod_final_path = os.path.join(config.get_mods_dir(), mod_dirname)

            old_path, _ = self._find_mod_path(mod_id)
            if old_path and old_path != mod_final_path:
                shutil.rmtree(old_path)

            if os.path.exists(mod_final_path):
                shutil.rmtree(mod_final_path)

            try:
                shutil.move(download_path, mod_final_path)
            except Exception as e:
                return False, f"Failed to install mod: {e}"
                
            mod_info = {
                "mod_id": mod_id,
                "title": title,
                "folder_name": mod_dirname,
                "steam_time_updated": steam_details.get("time_updated", 0) if steam_details else 0,
                "local_install_time": int(time.time()),
                "enabled": True,
                "is_contraption": is_contraption
            }
            self._write_mod_info(mod_final_path, mod_info)

        if temp_dir is not None and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

        if config.active_game == "pz":
            return True, f"Project Zomboid mod '{title}' installed successfully"
        elif is_contraption and config.active_game == "ppg":
            return True, f"Contraption '{title}' installed successfully"
        else:
            return True, f"Mod '{title}' installed successfully"

    def _download_with_steamcmd(self, mod_id):
        steamcmd_exe = os.path.join(config.steamcmd_dir, config.steamcmd_exe_name)
        if not os.path.isfile(steamcmd_exe):
            return False, None, "SteamCMD not found"

        download_dir = os.path.join(config.steamcmd_dir, "Downloads")
        os.makedirs(download_dir, exist_ok=True)

        app_id = config.get_app_id()
        if not app_id:
            return False, None, "No active game configured"

        expected_path = os.path.join(download_dir, "steamapps", "workshop", "content", app_id, mod_id)

        if os.path.exists(expected_path):
            shutil.rmtree(expected_path)

        cmd = [
            steamcmd_exe,
            "+force_install_dir", download_dir,
            "+login", "anonymous",
            "+workshop_download_item", app_id, mod_id, "validate",
            "+quit"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=config.steamcmd_dir)

            if result.returncode == 0 and os.path.isdir(expected_path):
                return True, expected_path, "SteamCMD download successful"
            else:
                return False, None, "SteamCMD download failed"

        except Exception as e:
            return False, None, f"SteamCMD error: {e}"

    def _delete_mod(self, mod_id):
        mod_path, _ = self._find_mod_path(mod_id)
        if not mod_path:
            return False, f"Mod {mod_id} not found"

        try:
            shutil.rmtree(mod_path)
            return True, f"Mod deleted successfully"
        except Exception as e:
            return False, f"Failed to delete mod: {e}"

    def _check_mod_update(self, mod_id):
        mod_path, local_info = self._find_mod_path(mod_id)
        if not mod_path or not local_info:
            return {"mod_id": mod_id, "installed": False, "updateAvailable": False}

        steam_details = get_mod_details_from_steam(mod_id)
        if not steam_details:
            return {
                "mod_id": mod_id,
                "installed": True,
                "title": local_info.get("title"),
                "updateAvailable": False,
                "error": "Could not fetch Steam details",
                "enabled": local_info.get("enabled", True),
                "is_contraption": local_info.get("is_contraption", False)
            }

        local_time = local_info.get("steam_time_updated", 0)
        steam_time = steam_details["time_updated"]
        update_available = steam_time > local_time

        return {
            "mod_id": mod_id,
            "installed": True,
            "title": steam_details["title"],
            "updateAvailable": update_available,
            "localVersionTime": local_time,
            "steamVersionTime": steam_time,
            "enabled": local_info.get("enabled", True),
            "is_contraption": local_info.get("is_contraption", False)
        }

    def _check_all_mod_updates(self):
        results = []

        mods_dir = config.get_mods_dir()
        disabled_mods_dir = config.get_disabled_mods_dir()
        directories = [mods_dir]

        if config.active_game == "ppg":
            contraptions_dir = config.get_contraptions_dir()
            if contraptions_dir:
                directories.append(contraptions_dir)

        if disabled_mods_dir:
            directories.append(disabled_mods_dir)

        for directory in directories:
            if not os.path.isdir(directory):
                continue

            for folder_name in os.listdir(directory):
                mod_path = os.path.join(directory, folder_name)
                if not os.path.isdir(mod_path):
                    continue

                info = self._read_mod_info(mod_path)
                if info and "mod_id" in info:
                    results.append(self._check_mod_update(info["mod_id"]))

        return results

    def _toggle_mod(self, mod_id, enable):
        mod_path, mod_info = self._find_mod_path(mod_id)
        if not mod_path or not mod_info:
            return False, f"Mod {mod_id} not found"

        mods_dir = config.get_mods_dir()
        disabled_mods_dir = config.get_disabled_mods_dir()
        
        if config.active_game == "pz":
            folder_name = mod_info.get("folder_name")
            if not folder_name:
                return False, "Missing folder name in mod info"
                
            source_path = mod_path
            if enable:
                dest_path = os.path.join(mods_dir, folder_name)
            else:
                dest_path = os.path.join(disabled_mods_dir, folder_name)
                
            try:
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                    
                shutil.copytree(source_path, dest_path)
                
                if not enable:
                    shutil.rmtree(source_path)
                
                mod_info["enabled"] = enable
                self._write_mod_info(dest_path, mod_info)
                
                status = "enabled" if enable else "disabled"
                return True, f"Mod '{mod_info.get('title', mod_id)}' is now {status}"
            except Exception as e:
                logging.error(f"Error toggling Project Zomboid mod status: {e}")
                return False, f"Failed to update mod status: {e}"
        else:
            is_contraption = mod_info.get("is_contraption", False)
            if is_contraption and config.active_game == "ppg":
                mods_dir = config.get_contraptions_dir()

            source_dir = disabled_mods_dir if enable else mods_dir
            dest_dir = mods_dir if enable else disabled_mods_dir

            folder_name = mod_info.get("folder_name", os.path.basename(mod_path))

            dest_path = os.path.join(dest_dir, folder_name)

            try:
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)

                shutil.move(mod_path, dest_path)

                mod_info["enabled"] = enable
                self._write_mod_info(dest_path, mod_info)

                status = "enabled" if enable else "disabled"
                return True, f"Mod '{mod_info.get('title', mod_id)}' is now {status}"
            except Exception as e:
                logging.error(f"Error toggling mod status: {e}")
                return False, f"Failed to update mod status: {e}"


config = ModManagerConfig()

def run_server(port=8000):
    server = HTTPServer(('localhost', port), ModManagerHTTPHandler)
    logging.info(f"Server started on http://localhost:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutdown requested")
    finally:
        server.server_close()
        logging.info("Server shut down")

if __name__ == "__main__":
    game_dir = config.get_game_dir()
    steamcmd_path = os.path.join(config.steamcmd_dir, config.steamcmd_exe_name)

    if not game_dir or not os.path.isdir(game_dir) or \
       not config.steamcmd_dir or not os.path.isfile(steamcmd_path):
        logging.critical("Critical paths invalid. Exiting.")
        sys.exit(1)

    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            logging.root.removeHandler(handler)

    log_file = f"gog_mod_manager_{config.active_game}.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.root.addHandler(file_handler)

    logging.info(f"Starting GOG Mod Manager for {GAME_CONFIGS[config.active_game]['name']}")
    run_server()
