import sys
import traceback

from opensyslog_helper import OpensyslogHelper
from opensyslog_syslog import OpensyslogSyslog
import restful_server

class OpensyslogMonitor:
    def __init__(self, config_folder):
        self.helper = OpensyslogHelper(config_folder)
        self.helper.print(self.helper.log_level_info, "OpensyslogMonitor: Starting Monitor")

        restful_server.restful_server_start(self.helper)
        self.syslog = OpensyslogSyslog(self.helper)
        while True:
            try:
                self.helper.print(self.helper.log_level_debug, "OpensyslogMonitor: Start syslog monitor loop")
                self.syslog.monitor()
            except Exception as e:
                exception_info = "OpensyslogMonitor:exception: {}\n Call Stack: {}".format(str(e), str(traceback.format_exc()))
                self.helper.print(self.helper.log_level_error, exception_info)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
        if not root_path.endswith("/"):
            root_path = root_path + "/"
    else:
        root_path = "/config/"
    print("Config folder: " + root_path)
    main_object = OpensyslogMonitor(root_path)
