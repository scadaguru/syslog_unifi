from flask import Flask, request, jsonify, make_response
import traceback
from threading import Thread
import datetime
import json
from collections import OrderedDict

restfulServerApp = Flask(__name__)
restfulServerHelper = None
server_ip = "0.0.0.0"
server_port = 8080
server_debug = False # must be false otherwise it gives runtime error!
restful_server_thread_handle = None

def restful_server_start(CommonHelper):
    global restfulServerHelper

    restfulServerHelper = CommonHelper

    try:
        restfulServerHelper.print(restfulServerHelper.log_level_debug, "restful_server_start: enter")
        restful_server_thread_handle = Thread(target=restful_server_thread)
        restful_server_thread_handle.start()
        restfulServerHelper.print(restfulServerHelper.log_level_debug, "restful_server_start: exit")
    except Exception as e:
        exception_info = "restful_server_start:exception: {}\n Call Stack: {}".format(str(e), str(traceback.format_exc()))
        restfulServerHelper.print(restfulServerHelper.log_level_error, exception_info)

def restful_server_thread():
    try:
        restfulServerApp.run(host=server_ip, port=server_port, debug=server_debug)
    except Exception as e:
        exception_info = "restful_server_thread:exception: {}\n Call Stack: {}".format(str(e), str(traceback.format_exc()))
        restfulServerHelper.print(restfulServerHelper.log_level_error, exception_info)

@restfulServerApp.route('/', methods=['GET'])
@restfulServerApp.route("/reconnect", methods=['GET'])
def get_webpage_sortby_reconnect_count_desc():
    html_str = "No data!"
    dhcp_ack_json = restfulServerHelper.load_dhcpack_status_json()
    if len(dhcp_ack_json) > 0:
      sorted_json = OrderedDict(sorted(dhcp_ack_json.items(), key=get_reconnect_count, reverse=True))  # sorts by Max reconnect count
      html_str = f"Count: {len(dhcp_ack_json)}, Sorted: reconnect count (desc)<br/>"
      return html_str + generate_html(sorted_json)
    return html_str

@restfulServerApp.route("/datetime", methods=['GET'])
def get_webpage_sortby_datetime_desc():
    html_str = "No data!"
    dhcp_ack_json = restfulServerHelper.load_dhcpack_status_json()
    if len(dhcp_ack_json) > 0:
      sorted_json = OrderedDict(sorted(dhcp_ack_json.items(), key=lambda item: get_sorting_key_datetime(item[1]), reverse=True))
      html_str = f"Count: {len(dhcp_ack_json)}, Sorted: datetime (desc)<br/>"
      return html_str + generate_html(sorted_json)
    return html_str

@restfulServerApp.route("/ip", methods=['GET'])
def get_webpage_sortby_ip_address():
    html_str = "No data!"
    dhcp_ack_json = restfulServerHelper.load_dhcpack_status_json()
    if len(dhcp_ack_json) > 0:
      sorted_json = OrderedDict(sorted(dhcp_ack_json.items(), key=lambda item: get_sorting_key_ip(item[1])))
      html_str = f"Count: {len(dhcp_ack_json)}, Sorted: IP (asc)<br/>"
      return html_str + generate_html(sorted_json)
    return html_str

def generate_html(sorted_json):
    html_str = "<table cellspacing=0px border=1><tr><th>MAC Address</th><th>IP Address</th><th>Client Name</th><th>Reconnect Count Per Day</th><th>Last connected</th></tr>"
    for key, value in sorted_json.items():
        html_str += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(key, value["ip"], value["name"], value["reconnect_count_per_day"], value["last_connected"])
    html_str += "</table>"
    return html_str

@restfulServerApp.route("/notifications", methods=['GET'])
def get_webpage_notifications():
    html_str = "No data!"
    history_json = restfulServerHelper.load_notification_history_json()
    if len(history_json) > 0:
        requested = request.args.get('last', "")
        max = len(history_json)
        if requested.isdigit():
            max = int(requested)
        html_str = f"Count: {max}/{len(history_json)}, Sorted: datetime (desc)<br/>"
        html_str += "<table cellspacing=0px border=1><tr><th>Datetime</th><th>Notification</th></tr>"
        sorted_json = OrderedDict(sorted(history_json.items(), reverse=True))
        counter = 1
        for key, value in sorted_json.items():
            html_str += "<tr><td>{}</td><td>{}</td></tr>".format(key, value)
            counter += 1
            if counter > max:
                break
        html_str += "</table>"
    return html_str
  
def get_reconnect_count(item):
    reconnect_count = 0
    reconnect_count_str = item[1].get("reconnect_count_per_day")
    if reconnect_count_str != None:
        reconnect_count = int(reconnect_count_str)
    return reconnect_count

def get_sorting_key_datetime(item):
    return (item['last_connected'], item['reconnect_count_per_day'])

def get_sorting_key_ip(item):
    split_ip = item["ip"].split(".")
    return (int(split_ip[0]), int(split_ip[1]), int(split_ip[2]), int(split_ip[3]))

#############################################################################################################

# if __name__ == '__main__':
    #app.run(host=server_data['host_server'], debug=False, port=server_data['port_number'])
