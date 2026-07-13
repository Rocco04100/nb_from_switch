import json

from netmiko import ConnectHandler
from netmiko.ssh_autodetect import SSHDetect

# from netmiko.ssh_exception import (
#     NetmikoAuthenticationException,
#     NetmikoTimeoutException,
# )
# Was having errors using this worth another try sometime

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
    outputs_dict = {}
    net_connect = None
    if os_type is None:
        print("Operating Sytem not detected aborting...")
        return

    switch["device_type"] = os_type
    net_connect = ConnectHandler(**switch)

    if isinstance(
        commands, str
    ):  # convert single string command to list so for loop can work with single commands too
        commands = [commands]

    for command in commands:
        try:
            output = net_connect.send_command(
                command, read_timeout=30, use_textfsm=True
            )
            if isinstance(output, list):
                print(f"--- {command} (Parsed) ---")
                outputs_dict[command] = output
            else:
                print(f"--- {command} (Raw) ---")
                # if text is not parsed it still adds raw output but flags it with COMMAND NOT PARSED
                outputs_dict[command] = {
                    "COMMAND NOT PARSED": command,
                    "raw_output": output,
                }

                print(f"{command} not parsed added to output as COMMAND NOT PARSED")

        except Exception as e:
            print(
                f"Command Error(usually wrong output due to syntax error in command): {e}"
            )

    if net_connect:
        net_connect.disconnect()
        print("\nConnection closed.")
    return outputs_dict


def parse_connected_devices(raw_data):
    """
    Correlates ARP, MAC Table, and LLDP data.
    Includes fallback parsing if TextFSM fails.
    """
    connected_devices = []
    # -----------------------------------------------------------------
    # 1. Build Lookup Dictionaries
    # Build dict to look up MAC -> IP (from show ip ARP)
    # ----------------------------------------------------------------
    arp_table = {}
    arp_data = raw_data.get("show ip arp", [])
    print("DEBUG: arp data printout")
    print(f"{arp_data}")

    for entry in arp_data:
        mac = entry.get("mac_address", "")
        mac = str(mac).replace(".", "").replace(":", "").upper()

        ip = entry.get("ip_address", "")
        # print(f"DEBUG: Test grabbing ip from raw show ip arp -> {ip} ")
        arp_table[mac] = ip
        # print(f"DEBUG: test arp table filling -> {arp_table}")

        if mac and ip != "Incomplete":
            print(f"DEBUG: ARP Entry - MAC: {mac}, IP: {ip}")

    print(f"DEBUG: arp table right after creation -> {arp_table}")
    # ----------------------------------------------------------------
    # Building MAC -> Interface (from MAC Address Table)
    # ----------------------------------------------------------------
    mac_table = {}
    mac_data = raw_data.get("show mac address-table dynamic", [])

    for entry in mac_data:
        mac = entry.get("destination_address", "")
        if isinstance(mac, list):
            mac = mac[0] if mac else ""
        mac = str(mac).replace(".", "").replace(":", "").upper()

        port = entry.get("destination_port", "")
        if isinstance(port, list):
            ports_to_add = [str(p) for p in port if p]
        else:
            ports_to_add = [str(port)] if port else []

        if mac and ports_to_add:
            if mac not in mac_table:
                mac_table[mac] = []
            for p in ports_to_add:
                if p not in mac_table[mac]:
                    mac_table[mac].append(p)
            print(f"DEBUG: MAC Table Entry - MAC: {mac}, Ports: {ports_to_add}")

    # 2. Process LLDP Neighbors
    lldp_data = raw_data.get("show lldp neighbors detail", [])
    lldp_devices = {}

    if isinstance(lldp_data, list):
        for neighbor in lldp_data:
            remote_host = neighbor.get("neighbor", "")
            if isinstance(remote_host, list):
                remote_host = remote_host[0] if remote_host else ""

            local_port = neighbor.get("local_interface", "")
            if isinstance(local_port, list):
                local_port = local_port[0] if local_port else ""
            local_port = str(local_port)

            if remote_host and local_port:
                lldp_devices[local_port] = {
                    "hostname": remote_host,
                    "is_network_device": True,
                }

    # 3. Correlate all look up tables to build Final List
    #
    print(
        f"\nDEBUG: ARP Table Size: {len(arp_table)}, MAC Table Size: {len(mac_table)}"
    )

    for mac, ports in mac_table.items():
        print(f"DEBUG:ARP TABLE right before grabbing it {arp_table}")
        ip_address = arp_table.get(mac, None)

        if ip_address is None:
            print(f"DEBUG: MAC {mac} found in MAC table but NOT in ARP table")

        for port in ports:
            device_info = {
                "switch_port": port,
                "mac_address": ":".join([mac[i : i + 2] for i in range(0, 12, 2)]),
                "ip_address": ip_address,
                "hostname": None,
                "is_network_device": False,
                "source": "MAC_ARP_CORRELATION",
            }

            if port in lldp_devices:
                device_info["hostname"] = lldp_devices[port]["hostname"]
                device_info["is_network_device"] = True
                device_info["source"] = "LLDP"

            connected_devices.append(device_info)

    return connected_devices


# ---------------------------------------------------------------------
# EXECUTING FUNCTIONS
# ---------------------------------------------------------------------

detected_os = "cisco_ios"
commands = [
    # "show version",
    # "show interfaces",
    # "show ip interface brief",
    # "show interface status",
    "show ip arp",  # Maps IP -> MAC
    "show mac address-table dynamic",  # Maps MAC -> Port
    "show lldp neighbors detail",  # Identifies Network Devices
]
output = send_command(detected_os, commands)

if output:
    print("\n--- Final Output (JSON) ---")
    # json.dumps converts the list of dictionaries to a JSON formatted string
    # indent=4 makes it human-readable with 4 spaces of indentation
    with open("output.json", "w") as f:
        json.dump(output, f, indent=4)
    print("\nData saved to output.json")
else:
    print("No output generated.")
if output:
    # Parse the correlation data
    neighbors = parse_connected_devices(output)

    print("\n--- Connected Devices (NetBox Ready) ---")
    print(json.dumps(neighbors, indent=4))

    # Optional: Save to file
    with open("connected_devices.json", "w") as f:
        json.dump(neighbors, f, indent=4)
    print("\nData saved to connected_devices.json")
else:
    print("No output generated.")
