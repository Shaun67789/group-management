import json
import os
import threading

DATA_FILE = "data.json"

DEFAULT_DATA = {
    "config": {
        "bot_token": "8111600420:AAHT5BQEjE-065HxDFUrhvrsv2bb72nzr3s",
        "is_running": False,
        "owner_username": "Delete_ee"
    },
    "groups": {},
    "users": {}
}

class Database:
    def __init__(self, filepath=DATA_FILE):
        self.filepath = filepath
        self.lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump(DEFAULT_DATA, f, indent=4)

    def _read(self):
        with open(self.filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return DEFAULT_DATA.copy()

    def _write(self, data):
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def get_config(self):
        with self.lock:
            data = self._read()
            return data.get("config", {})

    def update_config(self, key, value):
        with self.lock:
            data = self._read()
            if "config" not in data:
                data["config"] = {}
            data["config"][key] = value
            self._write(data)

    def ensure_group(self, chat_id):
        str_id = str(chat_id)
        with self.lock:
            data = self._read()
            if "groups" not in data:
                data["groups"] = {}
            if str_id not in data["groups"]:
                data["groups"][str_id] = {
                    "rules": "No rules set yet. Use /setrules to set them.",
                    "welcome_message": "Welcome to the group!",
                    "bad_words": [],
                    "filters": {}
                }
                self._write(data)

    def get_group(self, chat_id):
        self.ensure_group(chat_id)
        with self.lock:
            return self._read()["groups"].get(str(chat_id))

    def update_group_setting(self, chat_id, key, value):
        self.ensure_group(chat_id)
        with self.lock:
            data = self._read()
            data["groups"][str(chat_id)][key] = value
            self._write(data)

    def add_filter(self, chat_id, trigger, filter_data):
        self.ensure_group(chat_id)
        with self.lock:
            data = self._read()
            data["groups"][str(chat_id)]["filters"][trigger.lower()] = filter_data
            self._write(data)
            
    def remove_filter(self, chat_id, trigger):
        self.ensure_group(chat_id)
        with self.lock:
            data = self._read()
            if trigger.lower() in data["groups"][str(chat_id)]["filters"]:
                del data["groups"][str(chat_id)]["filters"][trigger.lower()]
                self._write(data)

    def ensure_user(self, user_id, name="Unknown"):
        str_id = str(user_id)
        with self.lock:
            data = self._read()
            if "users" not in data:
                data["users"] = {}
            if str_id not in data["users"]:
                data["users"][str_id] = {
                    "warnings": 0,
                    "name": name,
                    "role": "member"
                }
                self._write(data)
            else:
                if name != "Unknown":
                    data["users"][str_id]["name"] = name
                    self._write(data)

    def get_user(self, user_id):
        str_id = str(user_id)
        with self.lock:
            return self._read().get("users", {}).get(str_id, {})

    def add_warning(self, user_id, name="Unknown"):
        self.ensure_user(user_id, name)
        with self.lock:
            data = self._read()
            data["users"][str(user_id)]["warnings"] += 1
            warnings = data["users"][str(user_id)]["warnings"]
            self._write(data)
            return warnings

    def reset_warnings(self, user_id):
        str_id = str(user_id)
        with self.lock:
            data = self._read()
            if "users" in data and str_id in data["users"]:
                data["users"][str_id]["warnings"] = 0
                self._write(data)

    def get_all_stats(self):
        with self.lock:
            data = self._read()
            return {
                "total_users": len(data.get("users", {})),
                "total_groups": len(data.get("groups", {}))
            }

db = Database()
