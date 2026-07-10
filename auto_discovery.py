# Serial port /dev/ttyUSB0

from netmiko import ConnectHandler
from netmiko.ssh_autodetect import SSHDetect

switch = {
    "device_type": "autodetect",
    "host": "192.168.1.2",
    "username": "admin",
    "password": "password1",
    # "secret": "",
}

print(f"Connecting to {switch['host']} ...")

try:
    guesser = SSHDetect(**switch)
    best_match = guesser.autodetect()

    if not best_match:
        raise Exception("Auto-detection failed. Could not identify device OS.")

    print(f"✅ Detected OS: {best_match}")
    # net_connect = ConnectHandler(**cisco_switch)

    # v_output = net_connect.send_command("show version", read_timeout=30)

    # print("\n--- Show Version Output ---\n")
    # print(v_output)

    # m_output = net_connect.send_command("show mac address-table", read_timeout=30)
    # print("\n--- Show mac Output ---\n")
    # print(m_output)

    # net_connect.disconnect()
    # print("\nConnection closed.")

except Exception as e:
    print(f"\nConnection failed: {e}")
