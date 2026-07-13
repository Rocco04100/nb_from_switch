# Serial port /dev/ttyUSB0

from netmiko import ConnectHandler
from netmiko.ssh_autodetect import SSHDetect

# from netmiko.ssh_exception import (
#     NetmikoAuthenticationException,
#     NetmikoTimeoutException,
# )

switch = {
    "device_type": "autodetect",
    "host": "192.168.1.2",
    "username": "admin",
    "password": "password1",
    # "secret": "",
    "conn_timeout": 15,
    "auth_timeout": 15,
    "global_delay_factor": 2,
}

print(f"Connecting to {switch['host']}...")


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


def send_command(os_type, commands: list):

    net_connect = None
    if os_type is None:
        print("Operating Sytem not detected aborting...")
        return

    switch["device_type"] = os_type
    net_connect = ConnectHandler(**switch)

    if isinstance(commands, str):  # convert single string command to list
        commands = [commands]

    for command in commands:
        try:
            output = net_connect.send_command(
                command, read_timeout=30, use_textfsm=True
            )
            if isinstance(output, list):
                print(f"\n--- {command} (Parsed) ---")
                for row in output:
                    print(row)
            else:
                print(f"\n--- {command} (Raw) ---")
                print(output)

        # except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        #     print(f"❌ Connection Error: {e}")
        except Exception as e:
            print(
                f"Command Error(usually wrong output due to syntax error in command): {e}"
            )

    if net_connect:
        net_connect.disconnect()
        print("\nConnection closed.")


detected_os = "cisco_ios"
commands = ["show ip interface brief", "show interface status"]
send_command(detected_os, commands)
