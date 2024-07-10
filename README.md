# syslog_unifi
Docker based syslog server for Unifi Network application

An application to notify when a network device gets connected to Unifi Network application!
I have tested it on UCG Ultra which runs Unifi Network application.

## You will need:
    1. Unifi Network application
    2. Telegram API token and chat-id

## How this works:
    This docker based application runs as syslog server and you will have to configure your Unifi Network application to send syslog to this app!
    Make sure to rename config.yaml.example to config.yaml and make required changes to that file before running the app!

## This app will create a logs and will store two kinds of logs:
    1. Application log: Logs generated by this application
    2. Syslog: Row data received from the Unifi Network application

## This app will create two json files:
    1. unifi_dhcpack_status.json: Which has detials of each netowrk client gets connected to your Unifi Network application
    2. notification_history.json: Which has details of notifications generated by this app and sent to Telegram app

## This app has web GUI:
    Web GUI can be access locally by the IP:PORT as per configured by the config.yaml file
    Typically: 192.168.1.100:8085
    These are URLs which gives some useful information!
    
        http://192.168.1.100:8085 This will give the history of the connected network clients to your Unifi Network application
        http://192.168.1.100:8085/datetime This will give the history of the connected network clients to your Unifi Network application (sorted by datetime desc)
        http://192.168.1.100:8085/ip This will give the history of the connected network clients to your Unifi Network application (sorted by IP address)
        http://192.168.1.100:8085/reconnect This will give the history of the connected network clients to your Unifi Network application (sorted by reconnect count desc)

        http://192.168.1.100:8085/notifications This will give the all history of the notifications generated by this application (sorted by datetime desc)
        http://192.168.1.100:8085/notifications/?last=100 This will give the last 100 history of the notifications generated by this application (sorted by reconnect count desc)
