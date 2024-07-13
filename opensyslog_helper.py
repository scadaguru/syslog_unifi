import datetime
import os
import json
import csv
import traceback
import yaml
import requests

import const

class OpensyslogHelper:
    log_level_debug = 1
    log_level_info = 2
    log_level_warning = 3
    log_level_error = 4
    log_level_critical = 5

    def __init__(self, config_folder):
        self.mac_to_name_lookup_dict = {}
        self.config_folder = config_folder
        self.config = yaml.safe_load(open(self.config_folder + const.APP_CONFIG_FILE))

        self.log_level = 2
        if self.config["logs"]["level"] == "debug":
            self.log_level = 1
        elif self.config["logs"]["level"] == "info":
            self.log_level = 2
        elif self.config["logs"]["level"] == "warning":
            self.log_level = 3
        elif self.config["logs"]["level"] == "error":
            self.log_level = 4
        elif self.config["logs"]["level"] == "critical":
            self.log_level = 5

        self.log_folder = self.config_folder + "logs/"
        self.syslog_log = self.log_folder + self.config["logs"]["syslog_log"]
        self.monitor_log = self.log_folder + self.config["logs"]["monitor_log"]
        self.log_purge_after_days = self.config["logs"]["purge_after_days"]
        
        self.bot_token = self.config['telegram']['api_token']
        self.bot_chat_id = self.config['telegram']['chat_id']
        self.base_url = "https://api.telegram.org/bot" + self.bot_token
        if self.log_level == 1:
            self.notify_telegram("Unifi syslog got started!")

        if not os.path.exists(self.log_folder):
            os.makedirs(self.config_folder + "logs")
            self.print(self.log_level_info, "OpensyslogHelper:__init__(): Creating folder: " + self.log_folder)

        self.setup_lookup_csv_file()

    def get_log_level_to_string(self, log_level):
        log_level_str = ": "
        if log_level == self.log_level_debug:
            log_level_str = ":debug: "
        elif log_level == self.log_level_info:
            log_level_str = ":info: "
        elif log_level == self.log_level_warning:
            log_level_str = ":warn: "
        elif log_level == self.log_level_error:
            log_level_str = ":error: "
        elif log_level == self.log_level_critical:
            log_level_str = ":critical: "
        return log_level_str

    def log_data(self, message_data):
        self.print(self.log_level_debug, "OpensyslogHelper:ld(): enter")
        try:
            log_file_name = self.syslog_log + "-" + datetime.datetime.now().strftime('%Y-%m-%d') + ".log"
            log_str = ""
            if self.config["logs"]["prepend_timestamp"] == True:
                log_str = datetime.datetime.now().strftime('%H:%M:%S') + "::: "
            log_str = log_str + message_data
            if self.config["logs"]["append_new_line"] == True:
                log_str = log_str + "\n"

            # just check exist or not and set flag, and once written and closed that file then call purge to avoid recursive loop
            need_to_purge_files = not os.path.isfile(log_file_name)
            with open(log_file_name, "a") as log_file:
                log_file.write(log_str)
                if need_to_purge_files:
                    self.purge_older_files()

        except Exception as e:
            self.print(self.log_level_error, "ErxHelper:log_data():Exception:" + str(e))
        self.print(self.log_level_debug, "OpensyslogHelper:ld(): exit")

    def print(self, log_level, str_print):
        if self.log_level > log_level:
            return
        try:
            log_file_name = self.monitor_log + "-" + datetime.datetime.now().strftime('%Y-%m-%d') + ".log"
            log_str = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3] + \
                      self.get_log_level_to_string(log_level) + str_print

            print(log_str)
            with open(log_file_name, "a") as log_file:
                log_file.write(log_str + "\n")
        except Exception as e:
            print(datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3] + " : OpensyslogHelper:print():Exception: " +
                  str(e))

    def purge_older_files(self):
        current_date = datetime.datetime.today()
        self.print(self.log_level_debug, "About to call purge")
        for root, directories, files in os.walk(self.log_folder, topdown=False):
            for name in files:
                file_date = os.stat(os.path.join(root, name))[8]
                file_age = current_date - \
                    datetime.datetime.fromtimestamp(file_date)
                if file_age.days > self.log_purge_after_days:
                    file_name_with_path = os.path.join(root, name)
                    str_print = f"Purged file: {file_name_with_path}, age: {file_age.days}"
                    self.print(self.log_level_info, str_print)
                    os.remove(file_name_with_path)
        self.print(self.log_level_debug, "Finished purging older files")

    def load_dhcpack_status_json(self):
        return self.load_json_file(self.config_folder + const.JSON_FILE_UNIFI_DHCPACK_FILE)

    def save_dhcpack_status_json(self, dhcp_ack_json):
        self.save_json_file(self.config_folder + const.JSON_FILE_UNIFI_DHCPACK_FILE, dhcp_ack_json)

    def load_notification_history_json(self):
        return self.load_json_file(self.config_folder + const.JSON_FILE_NOTIFICATION_HIST_FILE)

    def append_notification_history(self, notification_text):
        history_json = self.load_json_file(self.config_folder + const.JSON_FILE_NOTIFICATION_HIST_FILE)
        date_time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        history_json[date_time_now] = notification_text
        self.save_notification_history(history_json)

    def save_notification_history(self, notification_history_json):
        self.save_json_file(self.config_folder + const.JSON_FILE_NOTIFICATION_HIST_FILE, notification_history_json)

    def load_json_file(self, file_with_path):
        json_data = {}
        try:
            if os.path.exists(file_with_path):
                with open(file_with_path, 'r') as file_handle_read:
                    json_data = json.load(file_handle_read)
        except IOError as e:
            exception_info = f"load_json_file: {file_with_path}: exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.print(self.log_level_error, exception_info)
        return json_data

    def save_json_file(self, file_with_path, json_data):
        try:
            with open(file_with_path, 'w') as file_handle_write:
                file_handle_write.write(json.dumps(json_data, indent=4))
        except IOError as e:
            exception_info = f"save_json_file: {file_with_path}: exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.print(self.log_level_error, exception_info)

    def notify_telegram(self, message_data):
        try:
            # telegram API: https://core.telegram.org/bots/api#sendmessage
            telegram_message_url = self.base_url + "/sendMessage"
            if message_data != "":
                data = {"chat_id": self.bot_chat_id, 'text': message_data, 'parse_mode' : 'HTML'}
                resp = requests.post(telegram_message_url, data=data, timeout=30)
                if resp.status_code == 200:
                    self.print(self.log_level_debug, "Sent message successfully")
                else:
                    err = f"sendMessage error: failed to send, status: {resp.status_code}, reason: {resp.reason}, text: {resp.text}"
                    self.print(self.log_level_error, err)
        except Exception as e:
            exception_info = f"notify_telegram: exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.print(self.log_level_error, exception_info)

    def setup_lookup_csv_file(self):
        self.mac_to_name_lookup_dict = {}
        try:
            lookup_key = self.config.get("client_name_lookup", "")
            if lookup_key is not None:
                file_name = self.config["client_name_lookup"].get("csv_file_name", "").strip()
                if file_name is not None and len(file_name) > 0:
                    file_name_with_path = self.config_folder + file_name
                    if os.path.exists(file_name_with_path):
                        with open(file_name_with_path, "r") as csv_file:
                            self.mac_to_name_lookup_col_for_mac = self.config["client_name_lookup"].get("column_for_mac", "").strip()
                            self.mac_to_name_lookup_col_for_name = self.config["client_name_lookup"].get("column_for_name", "").strip()
                            for row in csv.DictReader(csv_file):
                                self.mac_to_name_lookup_dict[row[self.mac_to_name_lookup_col_for_mac].upper()] = row[self.mac_to_name_lookup_col_for_name]
                            self.print(self.log_level_info, f"Successfully loaded CSV lookup file with {len(self.mac_to_name_lookup_dict)} rows")
        except Exception as e:
            exception_info = f"setup_lookup_csv_file: exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.print(self.log_level_error, exception_info)

    def lookup_device_name_from_csv(self, mac_address):
        return self.mac_to_name_lookup_dict.get(mac_address.upper(), None)
