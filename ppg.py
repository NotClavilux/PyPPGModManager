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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from logging.handlers import RotatingFileHandler

PPG_APP_ID = "1118200"
MOD_INFO_FILE = "modinfo.json"

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
        self.ppg_dir = ""
        self.mods_dir = ""
        self.steamcmd_dir = ""
        self.steamcmd_exe_name = "steamcmd.exe" if platform.system() == "Windows" else "steamcmd.sh"
        self.config_file_path = self._get_config_path()
        self.load_config()

    def _get_config_path(self):
        if platform.system() == "Windows":
            config_dir = os.path.join(os.getenv('APPDATA', os.path.expanduser("~")), 'PyPPGModManager')
        else:
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'PyPPGModManager')

        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    def load_config(self):
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    data = json.load(f)

                self.ppg_dir = data.get("ppg_dir", "")
                self.steamcmd_dir = data.get("steamcmd_dir", "")

                if (self.ppg_dir and os.path.isdir(self.ppg_dir) and
                    self.steamcmd_dir and os.path.isfile(os.path.join(self.steamcmd_dir, self.steamcmd_exe_name))):
                    self.mods_dir = os.path.join(self.ppg_dir, "Mods")
                    os.makedirs(self.mods_dir, exist_ok=True)
                    logging.info(f"Config loaded successfully")
                    return
            except Exception as e:
                logging.error(f"Error loading config: {e}")

        self.setup_new_config()

    def setup_new_config(self):
        logging.info("Setting up new configuration")

        while True:
            self.ppg_dir = input(f"People Playground directory: ").strip()
            ppg_exe_win = os.path.join(self.ppg_dir, "People Playground.exe")
            ppg_exe_linux = os.path.join(self.ppg_dir, "People Playground.x86_64")

            if os.path.isdir(self.ppg_dir) and (os.path.exists(ppg_exe_win) or os.path.exists(ppg_exe_linux)):
                break
            print("Invalid PPG directory. Please try again.")

        self.mods_dir = os.path.join(self.ppg_dir, "Mods")
        os.makedirs(self.mods_dir, exist_ok=True)


        default_dir = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), 'PyPPGModManager', 'SteamCMD')
        steamcmd_input = input(f"SteamCMD directory (default: {default_dir}): ").strip()
        self.steamcmd_dir = steamcmd_input if steamcmd_input else default_dir
        os.makedirs(self.steamcmd_dir, exist_ok=True)


        steamcmd_path = os.path.join(self.steamcmd_dir, self.steamcmd_exe_name)
        if not os.path.isfile(steamcmd_path):
            if input("Download SteamCMD? (yes/no): ").lower() == 'yes':
                self.download_steamcmd()
            else:
                print("SteamCMD is required. Exiting.")
                sys.exit(1)


        self.save_config()

    def save_config(self):
        config_data = {"ppg_dir": self.ppg_dir, "steamcmd_dir": self.steamcmd_dir}
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
            return {
                "mod_id": details['publishedfileid'],
                "time_updated": details.get('time_updated', 0),
                "title": details.get('title', f'Mod {mod_id}')
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
            temp_zip = os.path.join(tempfile.gettempdir(), f"pyppg_{mod_id}.zip")

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
        if not os.path.isdir(config.mods_dir):
            return None, None

        for folder_name in os.listdir(config.mods_dir):
            mod_path = os.path.join(config.mods_dir, folder_name)
            if not os.path.isdir(mod_path):
                continue

            info_file = os.path.join(mod_path, MOD_INFO_FILE)
            if os.path.isfile(info_file):
                try:
                    with open(info_file, 'r') as f:
                        info = json.load(f)
                    if str(info.get("mod_id")) == str(mod_id):
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
                        "title": mod_info.get("title", "Unknown")
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
        success, download_path, message = self._download_with_steamcmd(mod_id)

        if not success:
            logging.info(f"SteamCMD failed, trying GGNetwork")
            temp_dir = tempfile.mkdtemp(prefix=f"pyppg_mod_{mod_id}_")
            success, download_path, message = download_mod_via_ggnetwork(mod_id, temp_dir)

        if not success or not download_path:
            return False, f"Failed to download mod: {message}"

        steam_details = get_mod_details_from_steam(mod_id)
        title = steam_details.get("title", f"Mod {mod_id}") if steam_details else f"Mod {mod_id}"

        safe_title = sanitize_filename(title)
        mod_dirname = f"{safe_title} [{mod_id}]"
        mod_final_path = os.path.join(config.mods_dir, mod_dirname)

        old_path, _ = self._find_mod_path(mod_id)
        if old_path and old_path != mod_final_path:
            shutil.rmtree(old_path)

        if os.path.exists(mod_final_path):
            shutil.rmtree(mod_final_path)

        try:
            shutil.move(download_path, mod_final_path)
        except Exception as e:
            return False, f"Failed to install mod: {e}"

        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

        mod_info = {
            "mod_id": mod_id,
            "title": title,
            "folder_name": mod_dirname,
            "steam_time_updated": steam_details.get("time_updated", 0) if steam_details else 0,
            "local_install_time": int(time.time()),
            "enabled": True
        }
        self._write_mod_info(mod_final_path, mod_info)

        return True, f"Mod '{title}' installed successfully"

    def _download_with_steamcmd(self, mod_id):
        steamcmd_exe = os.path.join(config.steamcmd_dir, config.steamcmd_exe_name)
        if not os.path.isfile(steamcmd_exe):
            return False, None, "SteamCMD not found"

        download_dir = os.path.join(config.steamcmd_dir, "Downloads")
        os.makedirs(download_dir, exist_ok=True)

        expected_path = os.path.join(download_dir, "steamapps", "workshop", "content", PPG_APP_ID, mod_id)

        if os.path.exists(expected_path):
            shutil.rmtree(expected_path)

        cmd = [
            steamcmd_exe,
            "+force_install_dir", download_dir,
            "+login", "anonymous",
            "+workshop_download_item", PPG_APP_ID, mod_id, "validate",
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
                "enabled": local_info.get("enabled", True)
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
            "enabled": local_info.get("enabled", True)
        }

    def _check_all_mod_updates(self):
        results = []
        if not os.path.isdir(config.mods_dir):
            return results

        for folder_name in os.listdir(config.mods_dir):
            mod_path = os.path.join(config.mods_dir, folder_name)
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

        mod_info["enabled"] = enable
        if self._write_mod_info(mod_path, mod_info):
            status = "enabled" if enable else "disabled"
            return True, f"Mod '{mod_info.get('title', mod_id)}' is now {status}"
        else:
            return False, f"Failed to update mod status"


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
    if not os.path.isdir(config.ppg_dir) or \
       not os.path.isfile(os.path.join(config.steamcmd_dir, config.steamcmd_exe_name)):
        logging.critical("Critical paths invalid. Exiting.")
        sys.exit(1)

    run_server()
