"""Module to process incoming syslog data from othe Uniti router"""
import socket
import time
import datetime
import traceback

import const

class OpensyslogSyslog:
    """Class to handle incoming syslog data from the Unifi router"""
    def __init__(self, opensysloghelper):
        self.dhcp_ack_json = {}
        self.helper = opensysloghelper
        self.default_notification_string = self.helper.config["notifications"].get("notification_string", const.DEFAULT_NOTIFICATION_STRING)
        self.default_notify_type = self.helper.config["notifications"].get("default_notify_type", const.NOTIFY_CONNECT_EACH_TIME_WITH_MAX_PER_DAY_WITH_INTERMITTENT)
        self.max_notify_count_per_device_per_day = self.helper.config["notifications"].get("max_notify_count_per_device_per_day", const.MAX_NOTIFY_COUNT_PER_DAY)
        self.dnd_start_hour = self.helper.config["notifications"].get("do_not_disturb_start_hour", const.DND_NOTIFY_START_HOUR)
        self.dnd_end_hour = self.helper.config["notifications"].get("do_not_disturb_end_hour", const.DND_NOTIFY_END_HOUR)
        msg_str = f"max_notify_count_per_device_per_day: {self.max_notify_count_per_device_per_day}, do_not_disturb_start_hour: {self.dnd_start_hour}, do_not_disturb_end_hour: {self.dnd_end_hour}"
        self.helper.print(self.helper.log_level_debug, msg_str)

    def monitor(self):
        """Read syslog data"""
        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:monitor(): enter")
        previous_string_data = ""

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((const.SYSLOG_SERVER_IP, const.SYSLOG_SERVER_PORT))
            while True:
                try:
                    data, address = sock.recvfrom(const.SYSLOG_SOCKET_RECEIVE_BUFFER)
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
        """Log syslog data"""
        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:hid(): enter")

        string_data = string_data.replace('\n', '')
        self.helper.log_data(string_data)
        self.parse_message_data(string_data)

        self.helper.print(self.helper.log_level_debug, "OpensyslogSyslog:hid(): exit")

    def parse_message_data(self, message_data):
        """Process syslog data"""
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
            first_time_seen = False
            if json_data is None:
                first_time_seen = True
                self.dhcp_ack_json[mac_address] = {"ip": ip_address, "name": client_name, "host_name": host_name, "reconnect_count_per_day": 1, "last_connected": date_time_now, "notify": self.default_notify_type}
            else:
                # This block is to auto correct unifi_dhcpack_status.json
                self.dhcp_ack_json[mac_address]["name"] = client_name # auto correct from the lookup file!
                self.dhcp_ack_json[mac_address]["host_name"] = host_name # auto correct from the lookup file!
                if isinstance(self.dhcp_ack_json[mac_address]["notify"], bool):
                    self.dhcp_ack_json[mac_address]["notify"] = self.default_notify_type # auto correct from the lookup file!
                # End auto correct
                if self.dhcp_ack_json[mac_address]["last_connected"].split()[0] != date_time_now.split()[0]:
                    self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] = 1
                else:
                    self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] += 1
            self.notify(mac_address, ip_address, first_time_seen)
            self.dhcp_ack_json[mac_address]["ip"] = ip_address
            self.dhcp_ack_json[mac_address]["last_connected"] = date_time_now
            self.helper.save_dhcpack_status_json(self.dhcp_ack_json)
        except Exception as e:
            exception_info = f"parse_message_data:exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.helper.print(self.helper.log_level_error, exception_info)

    def notify(self, mac_address, ip_address, first_time_seen):
        """Notify user of this event"""
        notified = False
        try:
            notify_msg = self.build_notification_string(mac_address, ip_address, first_time_seen)
            if self.is_notification_needed(mac_address, ip_address, first_time_seen) and self.is_currnet_time_outside_dnd():
                self.helper.notify_telegram(notify_msg)
                self.helper.print(self.helper.log_level_debug, "Notified: " + notify_msg)
                notified = True
            self.helper.append_notification_history(notify_msg + ", Notified: " + str(notified))
        except Exception as e:
            exception_info = f"notify:exception: {str(e)}\n Call Stack: {str(traceback.format_exc())}"
            self.helper.print(self.helper.log_level_error, exception_info)
        return notified

    def build_notification_string(self, mac_address, ip_address, first_time_seen):
        """Build string for notification"""
        notify_string = self.default_notification_string.replace("{MAC}", str(mac_address))
        notify_string = notify_string.replace("{IP}", str(ip_address))
        notify_string = notify_string.replace("{NAME}", str(self.dhcp_ack_json[mac_address]["name"]))
        notify_string = notify_string.replace("{COUNT}", str(self.dhcp_ack_json[mac_address]["reconnect_count_per_day"]))
        first_time_seen = f'{"<b>(New)</b> " if first_time_seen else ""}'
        ip_changed = f'{"<b>(IP-Changed)</b> " if self.dhcp_ack_json[mac_address]["ip"] != ip_address else ""}'
        return first_time_seen + ip_changed + notify_string

    def is_notification_needed(self, mac_address, ip_address, first_time_seen):
        """Check if notification needs to be sent"""
        match self.dhcp_ack_json[mac_address]["notify"]:
            case const.NOTIFY_NEVER:
                return False
            case const.NOTIFY_CONNECT_FIRST_TIME:
                return first_time_seen
            case const.NOTIFY_CONNECT_FIRST_TIME_OR_IP_HOPE:
                return first_time_seen or self.dhcp_ack_json[mac_address]["ip"] != ip_address
            case const.NOTIFY_CONNECT_EACH_TIME:
                return True
            case const.NOTIFY_CONNECT_EACH_TIME_WITH_MAX_PER_DAY:
                return self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] <= self.max_notify_count_per_device_per_day
            case const.NOTIFY_CONNECT_EACH_TIME_WITH_MAX_PER_DAY_WITH_INTERMITTENT:
                return (self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] <= self.max_notify_count_per_device_per_day) or \
                    self.dhcp_ack_json[mac_address]["reconnect_count_per_day"] % 10 == 1
            case const.NOTIFY_CONNECT_DEVICE_NOT_IN_LOOKUP_FILE:
                if self.helper.lookup_device_name_from_csv(mac_address):
                    return False
                return True
            case _:
                return False

    def is_currnet_time_outside_dnd(self):
        """Check if current datetime falls withing DND range"""
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
