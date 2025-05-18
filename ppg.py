import os
import sys
import json
import subprocess
import platform
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading
import requests
import shutil
import logging
from logging.handlers import RotatingFileHandler
import tempfile
import zipfile

PPG_APP_ID = "1118200"
MOD_INFO_FILE = "modinfo.json"

log_file = 'ppg_mod_manager.log'
log_dir = os.path.dirname(log_file)
if log_dir and not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        log_file = os.path.basename(log_file) if os.path.basename(log_file) else 'ppg_mod_manager.log'

rotating_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s [%(threadName)s] - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
                    handlers=[rotating_handler, logging.StreamHandler(sys.stdout)])

class ModManagerConfig:
    def __init__(self):
        self.ppg_dir = ""
        self.mods_dir = ""
        self.steamcmd_dir = ""
        self.config_file_path = self._get_config_file_path()
        self.steamcmd_exe_name = "steamcmd.exe" if platform.system() == "Windows" else "steamcmd.sh"
        self.load_or_initialize_config()

    def _get_config_file_path(self):
        if platform.system() == "Windows":
            app_data = os.getenv('APPDATA')
            config_dir_base = app_data if app_data else os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        else:
            xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
            config_dir_base = xdg_config_home

        config_dir = os.path.join(config_dir_base, 'PyPPGModManager')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    def load_or_initialize_config(self):
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.ppg_dir = data.get("ppg_dir", "")
                self.steamcmd_dir = data.get("steamcmd_dir", "")

                paths_valid = True
                if not self.ppg_dir or not os.path.isdir(self.ppg_dir):
                    paths_valid = False
                if not self.steamcmd_dir or not os.path.isfile(os.path.join(self.steamcmd_dir, self.steamcmd_exe_name)):
                    paths_valid = False

                if not paths_valid:
                    self.initial_setup()
                else:
                    self.mods_dir = os.path.join(self.ppg_dir, "Mods")
                    os.makedirs(self.mods_dir, exist_ok=True)
                    logging.info(f"Config loaded: PPG Dir: {self.ppg_dir}, Mods Dir: {self.mods_dir}, SteamCMD Dir: {self.steamcmd_dir}")
            except (json.JSONDecodeError, IOError, TypeError) as e:
                logging.error(f"Error loading config file {self.config_file_path}: {e}. Starting initial setup.")
                self.initial_setup()
        else:
            self.initial_setup()

    def save_config(self):
        config_data = {"ppg_dir": self.ppg_dir, "steamcmd_dir": self.steamcmd_dir}
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            logging.info(f"Configuration saved to {self.config_file_path}")
        except IOError as e:
            logging.error(f"Failed to save configuration: {e}")

    def initial_setup(self):
        logging.info("Starting initial setup for PyPPG Mod Manager")
        while True:
            self.ppg_dir = input(f"People Playground game directory (e.g., D:\\Steam\\steamapps\\common\\People Playground or /home/{os.getlogin()}/.steam/steam/steamapps/common/People Playground): ").strip()
            ppg_exe_win = os.path.join(self.ppg_dir, "People Playground.exe")
            ppg_exe_linux = os.path.join(self.ppg_dir, "People Playground.x86_64")
            if os.path.isdir(self.ppg_dir) and (os.path.exists(ppg_exe_win) or os.path.exists(ppg_exe_linux)):
                logging.info(f"PPG directory set: {self.ppg_dir}")
                break
            logging.error(f"Directory '{self.ppg_dir}' is not a valid PPG installation or does not exist.")

        self.mods_dir = os.path.join(self.ppg_dir, "Mods")
        os.makedirs(self.mods_dir, exist_ok=True)
        logging.info(f"Mods directory: {self.mods_dir}")

        default_steamcmd_base = os.getenv('APPDATA') if platform.system() == "Windows" else os.getenv('XDG_DATA_HOME', os.path.join(os.path.expanduser('~'), '.local', 'share'))
        suggested_steamcmd_dir = os.path.join(default_steamcmd_base, 'PyPPGModManager', 'SteamCMD')

        while True:
            steamcmd_dir_input = input(f"SteamCMD directory (where '{self.steamcmd_exe_name}' will be, default: {suggested_steamcmd_dir}): ").strip()
            self.steamcmd_dir = steamcmd_dir_input if steamcmd_dir_input else suggested_steamcmd_dir
            try:
                os.makedirs(self.steamcmd_dir, exist_ok=True)
                logging.info(f"SteamCMD directory set: {self.steamcmd_dir}")
                break
            except OSError as e:
                logging.error(f"Cannot create/access SteamCMD directory '{self.steamcmd_dir}': {e}.")

        steamcmd_exe_full_path = os.path.join(self.steamcmd_dir, self.steamcmd_exe_name)
        if not os.path.isfile(steamcmd_exe_full_path):
            logging.info(f"'{self.steamcmd_exe_name}' not found at {steamcmd_exe_full_path}.")
            if input(f"Download SteamCMD to {self.steamcmd_dir}? (yes/no): ").strip().lower() == 'yes':
                self.download_steamcmd()
                if not os.path.isfile(os.path.join(self.steamcmd_dir, self.steamcmd_exe_name)):
                    logging.critical(f"'{self.steamcmd_exe_name}' still not found after download. Exiting.")
                    sys.exit(1)
            else:
                logging.error(f"SteamCMD is required. Exiting.")
                sys.exit(1)

        self.save_config()
        logging.info("Initial configuration complete.")

    def download_steamcmd(self):
        logging.info(f"Downloading SteamCMD to {self.steamcmd_dir}")
        os.makedirs(self.steamcmd_dir, exist_ok=True)
        current_system = platform.system()
        archive_name, steamcmd_url = "", ""

        if current_system == "Windows":
            steamcmd_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            archive_name = "steamcmd.zip"
        elif current_system == "Linux":
            steamcmd_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
            archive_name = "steamcmd_linux.tar.gz"
        elif current_system == "Darwin":
            steamcmd_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_osx.tar.gz"
            archive_name = "steamcmd_osx.tar.gz"
        else:
            logging.error(f"Unsupported OS for SteamCMD download: {current_system}")
            return

        archive_path = os.path.join(self.steamcmd_dir, archive_name)
        try:
            response = requests.get(steamcmd_url, stream=True, timeout=60)
            response.raise_for_status()
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            logging.info(f"SteamCMD archive downloaded.")
            shutil.unpack_archive(archive_path, self.steamcmd_dir)
            logging.info("SteamCMD extracted.")
            os.remove(archive_path)
            if current_system != "Windows":
                steamcmd_sh_path = os.path.join(self.steamcmd_dir, "steamcmd.sh")
                if os.path.isfile(steamcmd_sh_path):
                    os.chmod(steamcmd_sh_path, 0o755)
                    logging.info(f"Made steamcmd.sh executable.")
                else:
                    found_sh = False
                    for root, _, files_in_root in os.walk(self.steamcmd_dir):
                        if "steamcmd.sh" in files_in_root:
                            actual_path = os.path.join(root, "steamcmd.sh")
                            target_path = os.path.join(self.steamcmd_dir, "steamcmd.sh")
                            if actual_path != target_path: shutil.move(actual_path, target_path)
                            os.chmod(target_path, 0o755)
                            logging.info(f"Found and made steamcmd.sh executable at {target_path}.")
                            found_sh = True
                            break
                    if not found_sh: logging.warning("steamcmd.sh not found after extraction.")
        except Exception as e:
            logging.error(f"SteamCMD download/setup error: {e}", exc_info=True)
            if os.path.exists(archive_path): os.remove(archive_path)

config = ModManagerConfig()

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else "Untitled Mod"

def get_steam_mod_details(mod_id):
    api_url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    payload = {'itemcount': 1, f'publishedfileids[0]': mod_id, 'format': 'json'}
    try:
        response = requests.post(api_url, data=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data['response']['result'] == 1 and data['response']['publishedfiledetails'][0].get('result') == 1:
            details = data['response']['publishedfiledetails'][0]
            return {"mod_id": details['publishedfileid'], "time_updated": details.get('time_updated', 0), "title": details.get('title', 'N/A')}
        return None
    except Exception as e:
        logging.error(f"Error fetching mod details for {mod_id}: {e}")
        return None

def download_mod_via_ggnetwork(mod_id, download_target_dir):
    logging.info(f"[GGN] Attempting download for mod {mod_id} via GGNetwork API.")
    api_url = "https://api.ggntw.com/steam.request"
    payload = {"url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"}
    headers = {
        'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://ggntw.com', 'Referer': 'https://ggntw.com/'
    }
    cdn_url_for_error = 'N/A'
    temp_zip_path_for_error = None
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get("result") == 1 and data.get("status") == "1" and "url" in data:
            cdn_url = data["url"]
            cdn_url_for_error = cdn_url
            mod_name_from_api = data.get("name", f"mod_{mod_id}")
            logging.info(f"[GGN] Received CDN URL for '{mod_name_from_api}': {cdn_url}")

            zip_response = requests.get(cdn_url, stream=True, timeout=120)
            zip_response.raise_for_status()

            os.makedirs(download_target_dir, exist_ok=True)
            temp_zip_path = os.path.join(tempfile.gettempdir(), f"pyppg_ggn_{mod_id}.zip")
            temp_zip_path_for_error = temp_zip_path

            with open(temp_zip_path, 'wb') as f_zip:
                for chunk in zip_response.iter_content(chunk_size=8192): f_zip.write(chunk)
            logging.info(f"[GGN] Downloaded ZIP to {temp_zip_path}")

            if not zipfile.is_zipfile(temp_zip_path):
                logging.error(f"[GGN] Downloaded file from {cdn_url} is not a valid ZIP file.")
                if os.path.exists(temp_zip_path): os.remove(temp_zip_path)
                return False, None, "GGN: Downloaded file was not a ZIP."

            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(download_target_dir)

            logging.info(f"[GGN] Extracted mod {mod_id} content to {download_target_dir}")
            if os.path.exists(temp_zip_path): os.remove(temp_zip_path)
            return True, download_target_dir, f"Successfully downloaded and extracted via GGNetwork."
        else:
            error_msg = data.get("error_msg") or f"API result not success or status not 1. Data: {data}"
            logging.error(f"[GGN] API request failed for mod {mod_id}: {error_msg}")
            return False, None, f"GGN: API Error - {error_msg}"
    except requests.exceptions.RequestException as e:
        logging.error(f"[GGN] Network error for mod {mod_id}: {e}")
        return False, None, f"GGN: Network Error - {e}"
    except zipfile.BadZipFile:
        logging.error(f"[GGN] Bad ZIP file for mod {mod_id} from URL {cdn_url_for_error}")
        if temp_zip_path_for_error and os.path.exists(temp_zip_path_for_error): os.remove(temp_zip_path_for_error)
        return False, None, "GGN: Downloaded file was a bad ZIP."
    except Exception as e:
        logging.error(f"[GGN] Unexpected error during GGNetwork download for mod {mod_id}: {e}", exc_info=True)
        if temp_zip_path_for_error and os.path.exists(temp_zip_path_for_error): os.remove(temp_zip_path_for_error)
        return False, None, f"GGN: Unexpected error - {e}"

class ModManagerHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format_str, *args):
        logging.info(f"{self.address_string()} - {format_str % args}")

    def _send_json_response(self, status_code, data):
        try:
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except Exception as e:
            logging.error(f"Error sending JSON response: {e}", exc_info=True)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _get_mod_folder_path_and_info(self, mod_id_to_find):
        if not os.path.isdir(config.mods_dir): return None, None
        for entry_name in os.listdir(config.mods_dir):
            potential_mod_path = os.path.join(config.mods_dir, entry_name)
            if os.path.isdir(potential_mod_path):
                modinfo_file = os.path.join(potential_mod_path, MOD_INFO_FILE)
                if os.path.isfile(modinfo_file):
                    try:
                        with open(modinfo_file, 'r', encoding='utf-8') as f: info = json.load(f)
                        if str(info.get("mod_id")) == str(mod_id_to_find):
                            return potential_mod_path, info
                    except (IOError, json.JSONDecodeError):
                        logging.warning(f"Could not read/parse {modinfo_file} in {potential_mod_path}")
        return None, None

    def _read_mod_info(self, mod_folder_path):
        modinfo_file = os.path.join(mod_folder_path, MOD_INFO_FILE)
        if os.path.isfile(modinfo_file):
            try:
                with open(modinfo_file, 'r', encoding='utf-8') as f: return json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Error reading {modinfo_file}: {e}")
        return None

    def _write_mod_info(self, mod_folder_path, mod_info_data):
        modinfo_file = os.path.join(mod_folder_path, MOD_INFO_FILE)
        try:
            with open(modinfo_file, 'w', encoding='utf-8') as f: json.dump(mod_info_data, f, indent=4)
            return True
        except IOError as e:
            logging.error(f"Error writing {modinfo_file}: {e}")
            return False

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)
        mod_id = query.get('id', [None])[0]
        action = parsed_path.path

        try:
            if action == '/status':
                self._send_json_response(200, {"status": "online", "version": "1.5.0"})

            elif action == '/is_installed':
                if not mod_id: self._send_json_response(400, {"error": "Missing mod ID"}); return
                mod_path, mod_info = self._get_mod_folder_path_and_info(mod_id)
                if mod_path and mod_info:
                    self._send_json_response(200, {"mod_id": mod_id, "installed": True, "enabled": mod_info.get("enabled", True), "title": mod_info.get("title", "N/A")})
                else:
                    self._send_json_response(200, {"mod_id": mod_id, "installed": False})

            elif action == '/install':
                if not mod_id: self._send_json_response(400, {"error": "Missing mod ID"}); return
                success, message = self.handle_install_mod(mod_id)
                self._send_json_response(200, {"success": success, "message": message})

            elif action == '/delete':
                if not mod_id: self._send_json_response(400, {"error": "Missing mod ID"}); return
                success, message = self.handle_delete_mod(mod_id)
                self._send_json_response(200, {"success": success, "message": message})

            elif action == '/check_update':
                if not mod_id: self._send_json_response(400, {"error": "Missing mod ID"}); return
                response_data = self.handle_check_single_mod_update(mod_id)
                self._send_json_response(200, response_data)

            elif action == '/check_updates':
                results = self.handle_check_all_mod_updates()
                self._send_json_response(200, {"success": True, "data": results})

            elif action == '/toggle_mod_enabled':
                if not mod_id: self._send_json_response(400, {"error": "Missing mod ID"}); return
                enable_param = query.get('enable', ['true'])[0].lower()
                should_enable = enable_param == 'true'
                success, message = self.handle_toggle_mod_enabled(mod_id, should_enable)
                self._send_json_response(200, {"success": success, "message": message})

            else:
                self._send_json_response(404, {"error": "Endpoint not found"})

        except BrokenPipeError: logging.warning(f"Broken pipe for {self.client_address} on {self.path}.")
        except ConnectionResetError: logging.warning(f"Connection reset by peer for {self.client_address} on {self.path}.")
        except Exception as e:
            logging.error(f"Error processing GET {action} for {self.client_address}: {e}", exc_info=True)
            if not self.wfile.closed: self._send_json_response(500, {"error": f"Internal server error: {e}"})

    def handle_install_mod(self, mod_id):
        steamcmd_exe_path = os.path.join(config.steamcmd_dir, config.steamcmd_exe_name)
        steamcmd_success = False
        steamcmd_download_path = None
        steamcmd_message = "SteamCMD primary download attempt."

        if not os.path.isfile(steamcmd_exe_path):
            steamcmd_message = "SteamCMD executable not found. Skipping SteamCMD."
            logging.warning(steamcmd_message)
        else:
            steamcmd_content_dl_dir = os.path.join(config.steamcmd_dir, "PyPPG_SteamCMD_Downloads")
            os.makedirs(steamcmd_content_dl_dir, exist_ok=True)

            expected_downloaded_item_path = os.path.join(steamcmd_content_dl_dir, "steamapps", "workshop", "content", PPG_APP_ID, mod_id)
            effective_download_item_path = expected_downloaded_item_path

            if os.path.exists(effective_download_item_path):
                logging.info(f"[SteamCMD] Clearing existing path: {effective_download_item_path}")
                shutil.rmtree(effective_download_item_path)

            cmd = [steamcmd_exe_path, "+force_install_dir", steamcmd_content_dl_dir, "+login", "anonymous", "+workshop_download_item", PPG_APP_ID, mod_id, "validate", "+quit"]
            logging.info(f"[SteamCMD] Running: {' '.join(cmd)}")

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=config.steamcmd_dir, encoding='utf-8', errors='replace')
                logging.debug(f"[SteamCMD] stdout for mod {mod_id}:\n{proc.stdout}")
                if proc.stderr: logging.debug(f"[SteamCMD] stderr for mod {mod_id}:\n{proc.stderr}")

                explicit_failure_string_in_output = f"ERROR! Download item {mod_id} failed".lower() in proc.stdout.lower()

                if explicit_failure_string_in_output:
                    error_context_start = proc.stdout.lower().find(f"ERROR! Download item {mod_id} failed".lower())
                    error_snippet = proc.stdout[error_context_start : error_context_start + 300]
                    steamcmd_message = f"SteamCMD explicitly failed to download mod {mod_id}. Snippet: ...{error_snippet}..."
                    logging.error(f"[SteamCMD] {steamcmd_message}")
                else:
                    has_success_string = "Success. Downloaded item" in proc.stdout or "already up to date" in proc.stdout
                    if proc.returncode == 0:
                        if has_success_string:
                            logging.info(f"[SteamCMD] Reported success string for mod {mod_id}.")
                            for line in proc.stdout.splitlines():
                                if "Success. Downloaded item" in line and "to \"" in line:
                                    try:
                                        path_from_output = line.split("to \"")[1].split("\"")[0]
                                        if os.path.commonpath([path_from_output, steamcmd_content_dl_dir]) == steamcmd_content_dl_dir:
                                            effective_download_item_path = path_from_output
                                    except IndexError: pass
                                    break
                            steamcmd_success = True
                            steamcmd_download_path = effective_download_item_path
                        elif os.path.isdir(expected_downloaded_item_path):
                            logging.warning(f"[SteamCMD] RC 0, no explicit success/failure, but expected dir exists. Proceeding.")
                            steamcmd_success = True
                            steamcmd_download_path = expected_downloaded_item_path
                        else:
                            steamcmd_message = f"SteamCMD RC 0 but no success indicators and target dir not found. Output: {proc.stdout[-300:]}"
                            logging.error(f"[SteamCMD] {steamcmd_message}")
                    else:
                        steamcmd_message = f"SteamCMD failed with RC {proc.returncode}. Output: {proc.stdout[-300:]}"
                        logging.error(f"[SteamCMD] {steamcmd_message}")
            except subprocess.TimeoutExpired:
                steamcmd_message = f"SteamCMD timed out for mod {mod_id}."
                logging.error(f"[SteamCMD] {steamcmd_message}")
            except Exception as e:
                steamcmd_message = f"SteamCMD execution error for mod {mod_id}: {e}"
                logging.error(f"[SteamCMD] {steamcmd_message}", exc_info=True)

        final_download_source_path = None
        ggn_temp_extract_dir_for_cleanup = None

        if steamcmd_success and steamcmd_download_path and os.path.isdir(steamcmd_download_path):
            logging.info(f"Using SteamCMD download for mod {mod_id} from {steamcmd_download_path}")
            final_download_source_path = steamcmd_download_path
        else:
            logging.warning(f"SteamCMD download failed or path invalid for mod {mod_id}. Reason: {steamcmd_message}. Attempting GGNetwork fallback.")
            ggn_temp_extract_dir = tempfile.mkdtemp(prefix=f"pyppg_ggn_extract_{mod_id}_")
            ggn_temp_extract_dir_for_cleanup = ggn_temp_extract_dir
            logging.info(f"Created temporary extraction directory for GGNetwork: {ggn_temp_extract_dir}")

            ggn_success, ggn_extracted_path, ggn_message = download_mod_via_ggnetwork(mod_id, ggn_temp_extract_dir)
            if ggn_success and ggn_extracted_path and os.path.isdir(ggn_extracted_path):
                logging.info(f"Using GGNetwork download for mod {mod_id} from {ggn_extracted_path}")
                final_download_source_path = ggn_extracted_path
            else:
                logging.error(f"Both SteamCMD and GGNetwork failed for mod {mod_id}. Last GGN error: {ggn_message}")
                if ggn_temp_extract_dir_for_cleanup and os.path.isdir(ggn_temp_extract_dir_for_cleanup): shutil.rmtree(ggn_temp_extract_dir_for_cleanup)
                return False, f"All download methods failed. SteamCMD: {steamcmd_message}. GGNetwork: {ggn_message}"

        if not final_download_source_path or not os.path.isdir(final_download_source_path):
            logging.error(f"No valid download source path found for mod {mod_id} after all attempts.")
            if ggn_temp_extract_dir_for_cleanup and os.path.isdir(ggn_temp_extract_dir_for_cleanup): shutil.rmtree(ggn_temp_extract_dir_for_cleanup)
            return False, "No valid download source path obtained."

        steam_details = get_steam_mod_details(mod_id)
        title_from_steam = steam_details.get("title", f"Mod {mod_id}") if steam_details else f"Mod {mod_id}"
        sanitized_title = sanitize_filename(title_from_steam)

        mod_final_dirname = f"{sanitized_title} [{mod_id}]"
        mod_final_path = os.path.join(config.mods_dir, mod_final_dirname)

        existing_mod_path, _ = self._get_mod_folder_path_and_info(mod_id)
        if existing_mod_path and existing_mod_path != mod_final_path :
             logging.info(f"Removing old mod folder during rename/update: {existing_mod_path}")
             shutil.rmtree(existing_mod_path)

        if os.path.exists(mod_final_path):
             logging.info(f"Removing existing content at final mod path for update: {mod_final_path}")
             shutil.rmtree(mod_final_path)

        try:
            shutil.move(final_download_source_path, mod_final_path)
            logging.info(f"Moved mod content from {final_download_source_path} to {mod_final_path}")
        except Exception as e:
            logging.error(f"Failed to move mod to Mods folder: {e}", exc_info=True)
            if ggn_temp_extract_dir_for_cleanup and final_download_source_path == ggn_temp_extract_dir_for_cleanup and os.path.isdir(final_download_source_path):
                logging.info(f"Cleaning up GGN temp directory after failed move: {final_download_source_path}")
                shutil.rmtree(final_download_source_path)
            return False, f"Failed to move mod to Mods folder: {e}"

        if ggn_temp_extract_dir_for_cleanup and final_download_source_path == ggn_temp_extract_dir_for_cleanup and os.path.exists(ggn_temp_extract_dir_for_cleanup):
             if not os.listdir(ggn_temp_extract_dir_for_cleanup):
                shutil.rmtree(ggn_temp_extract_dir_for_cleanup)
             else:
                logging.warning(f"GGN temp directory {ggn_temp_extract_dir_for_cleanup} was not empty after supposed move; manual cleanup might be needed.")


        mod_info_data = {
            "mod_id": mod_id, "title": title_from_steam, "folder_name": mod_final_dirname,
            "steam_time_updated": steam_details.get("time_updated", 0) if steam_details else 0,
            "local_install_time": int(time.time()), "enabled": True
        }
        self._write_mod_info(mod_final_path, mod_info_data)

        return True, f"Mod '{mod_info_data['title']}' installed/updated successfully."

    def handle_delete_mod(self, mod_id):
        mod_path, _ = self._get_mod_folder_path_and_info(mod_id)
        if mod_path:
            try:
                shutil.rmtree(mod_path)
                return True, f"Mod {mod_id} deleted from {mod_path}."
            except Exception as e: return False, f"Failed to delete mod {mod_id}: {e}"
        return False, f"Mod {mod_id} not found for deletion."

    def handle_check_single_mod_update(self, mod_id):
        mod_path, local_info = self._get_mod_folder_path_and_info(mod_id)
        if not mod_path or not local_info:
            return {"mod_id": mod_id, "installed": False, "updateAvailable": False, "message": "Mod not installed or info missing."}

        steam_details = get_steam_mod_details(mod_id)
        if not steam_details:
            return {"mod_id": mod_id, "installed": True, "title": local_info.get("title"), "updateAvailable": False, "error": "Could not fetch Steam details.", "enabled": local_info.get("enabled", True)}

        update_available = steam_details["time_updated"] > local_info.get("steam_time_updated", 0)
        return {
            "mod_id": mod_id, "installed": True, "title": steam_details["title"],
            "updateAvailable": update_available,
            "localVersionTime": local_info.get("steam_time_updated", 0),
            "steamVersionTime": steam_details["time_updated"],
            "enabled": local_info.get("enabled", True)
        }

    def handle_check_all_mod_updates(self):
        updates = []
        if not os.path.isdir(config.mods_dir): return updates
        for entry_name in os.listdir(config.mods_dir):
            potential_mod_path = os.path.join(config.mods_dir, entry_name)
            if os.path.isdir(potential_mod_path):
                mod_info = self._read_mod_info(potential_mod_path)
                if mod_info and "mod_id" in mod_info:
                    updates.append(self.handle_check_single_mod_update(mod_info["mod_id"]))
        return updates

    def handle_toggle_mod_enabled(self, mod_id, should_enable):
        mod_path, mod_info = self._get_mod_folder_path_and_info(mod_id)
        if not mod_path or not mod_info:
            return False, f"Mod {mod_id} not found."

        mod_info["enabled"] = should_enable
        if self._write_mod_info(mod_path, mod_info):
            status = "enabled" if should_enable else "disabled"
            logging.info(f"Mod '{mod_info.get('title', mod_id)}' status set to {status} in {MOD_INFO_FILE}.")
            return True, f"Mod '{mod_info.get('title', mod_id)}' is now {status}."
        return False, f"Failed to update {MOD_INFO_FILE} for {mod_id} after toggling state."

def run_server(port=8000):
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, ModManagerHTTPHandler)
    logging.info(f"PyPPG Mod Manager backend starting on http://{server_address[0]}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutdown requested via KeyboardInterrupt.")
    except Exception as e:
        logging.critical(f"Server crashed: {e}", exc_info=True)
    finally:
        httpd.server_close()
        logging.info("Server has shut down.")

if __name__ == "__main__":
    if not os.path.isdir(config.ppg_dir) or \
       not os.path.isfile(os.path.join(config.steamcmd_dir, config.steamcmd_exe_name)):
        logging.critical("Critical paths (PPG dir or SteamCMD) invalid after setup. Exiting.")
        sys.exit(1)
    run_server()
    logging.info("PyPPG Mod Manager backend has shut down.")
