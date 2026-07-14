import logging

import collector
import parse

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s - %(message)s",
)

logging.getLogger("netmiko").setLevel(logging.WARN)
logging.getLogger("paramiko").setLevel(logging.WARN)

# ---------------------------------------------------------------------
# EXECUTING FUNCTIONS
# ---------------------------------------------------------------------
commands = [
    # "show version",
    # "show interfaces",
    # "show ip interface brief",
    # "show interface status",
    "show ip arp",  # Maps IP -> MAC
    "show mac address-table dynamic",  # Maps MAC -> Port
    "show lldp neighbors detail",  # Identifies Network Devices
]
switch = {
    "device_type": "generic",
    "host": "192.168.1.2",
    "username": "admin",
    "password": "password1",
    # "secret": "",
    "conn_timeout": 15,
    "auth_timeout": 15,
    "global_delay_factor": 2,
}

output = collector.get_data(switch, commands)
neighbors = parse.connected_devices(output)
