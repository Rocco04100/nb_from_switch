import json

from netmiko.ssh_autodetect import SSHDetect

import collector
import parse


def detect_os():
    try:
        guesser = SSHDetect(**switch)
        best_match = guesser.autodetect()

        if not best_match:
            raise Exception("Auto-detection failed. Could not identify device OS.")

        print(f"✅ Detected OS: {best_match}")
        return best_match

    except Exception as e:
        print(f"\nConnection failed: {e}")
    return None


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
    "device_type": "cisco_ios",
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
