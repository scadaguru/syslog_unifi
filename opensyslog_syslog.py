import socket
import time
import json
import datetime
from collections import OrderedDict
import traceback

socket_receive_buffer = 4096
server_ip = "0.0.0.0"
server_port = 5142

class OpensyslogSyslog:
    def __init__(self, opensysloghelper):
        self.dhcp_ack_json = {}
        self.helper = opensysloghelper
        self.max_notify_count_per_device_per_day = self.helper.config["notifications"].get("max_notify_count_per_device_per_day", 5)
        self.dnd_start_hour = self.helper.config["notifications"].get("do_not_disturb_start_hour", 22)
        self.dnd_end_hour = self.helper.config["notifications"].get("do_not_disturb_end_hour", 8)
        msg_str = f"max_notify_count_per_device_per_day: {self.max_notify_count_per_device_per_day}, do_not_disturb_start_hour: {self.dnd_start_hour}, do_not_disturb_end_hour: {self.dnd_end_hour}"
        self.helper.print(self.helper.log_level_debug, msg_str)

    def monitor(self):
        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:monitor(): enter")
        previous_string_data = ""

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((server_ip, server_port))
            while True:
                try:
                    data, address = sock.recvfrom(socket_receive_buffer)
                    string_data = data.decode('utf-8')
                    if previous_string_data != string_data:
                        previous_string_data = string_data
                        self.handle_incoming_data(string_data)
                except Exception as e:
                    exception_info = f"OpensyslogSyslog:monitor():loop: exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
                    self.helper.print(self.helper.log_level_error, exception_info)
        except Exception as e:
            exception_info = f"OpensyslogSyslog:monitor(): exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.helper.print(self.helper.log_level_error, exception_info)
            time.sleep(60)
        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:monitor(): exit")

    def handle_incoming_data(self, string_data):
        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:hid(): enter")

        string_data = string_data.replace('\n', '')
        self.helper.log_data(string_data)
        self.parse_message_data(string_data)

        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:hid(): exit")

    def parse_message_data(self, message_data):
        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:pmd(): enter")

        try:
            index = -1
            data = message_data.split()
            for i, sub_data in enumerate(data):
                if "DHCPACK" in sub_data:
                    index = i
                    break
            if index == -1:
                return

            self.dhcp_ack_json = self.helper.load_dhcpack_status_json()
            host_name = None
            ip_address = data[index+1]
            mac_address = data[index+2].upper()
            if len(data) >= index+4:
                host_name = data[index+3]
            client_name = self.helper.lookup_device_name_from_csv(mac_address)
            if client_name is None:
                client_name = host_name
            json_data = self.dhcp_ack_json.get(mac_address)
            date_time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if json_data is None:
                self.dhcp_ack_json[mac_address] = {"ip": ip_address, "name": client_name, "host_name": host_name, "reconnect_count_per_day": 1, "last_connected": date_time_now, "notify": True}
            else:
                self.dhcp_ack_json[mac_address]["name"] = client_name # auto correct from the lookup file!
                self.dhcp_ack_json[mac_address]["host_name"] = host_name # auto correct from the lookup file!
                if self.dhcp_ack_json[mac_address]["last_connected"].split()[0] != date_time_now.split()[0]:
                    self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] = 1
                else:
                    self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] += 1
            self.dhcp_ack_json[mac_address]["last_connected"] = date_time_now
            self.helper.save_dhcpack_status_json(self.dhcp_ack_json)
            self.notify(mac_address)
        except Exception as e:
            exception_info = f"parse_message_data:exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.helper.print(self.helper.log_level_error, exception_info)

    def notify(self, mac_address):
        notify_msg = f'Network device got connected MAC: {mac_address}, IP: {self.dhcp_ack_json[mac_address]["ip"]}, Count: {self.dhcp_ack_json[mac_address]["reconnect_count_per_day"]}, Name: {self.dhcp_ack_json[mac_address]["name"]}'
        notified = False
        if self.dhcp_ack_json[mac_address]["notify"] and \
            (self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] < self.max_notify_count_per_device_per_day or self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] % 10 == 1) and \
            self.is_currnet_time_outside_dnd():

            self.helper.notify_telegram(notify_msg)
            self.helper.print(self.helper.log_level_debug, "Notified: " + notify_msg)
            notified = True
        self.helper.append_notification_history(notify_msg + ", Notified: " + str(notified))
        return notified

    def is_currnet_time_outside_dnd(self):
        current_datetime = datetime.datetime.now()
        dnd_start_datetime = datetime.datetime(current_datetime.year, current_datetime.month, current_datetime.day, self.dnd_start_hour, 0)
        dnd_end_datetime = datetime.datetime(current_datetime.year, current_datetime.month, current_datetime.day, self.dnd_end_hour, 0)
        if dnd_start_datetime <= dnd_end_datetime:
            status = dnd_start_datetime <= current_datetime <= dnd_end_datetime
        else:
            status = dnd_start_datetime <= current_datetime or current_datetime <= dnd_end_datetime
        msg_str = f"Current: {current_datetime}, start: {dnd_start_datetime}, end: {dnd_end_datetime}, outside: {not status}"
        self.helper.print(self.helper.log_level_debug, msg_str)
        return not status
