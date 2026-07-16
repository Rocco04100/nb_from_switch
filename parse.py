import json
import logging
import nb_utils


def create_arp_table(arp_data):
    arp_table = {}
    for entry in arp_data:
        mac = entry.get("mac_address", "")
        mac = str(mac).replace(".", "").replace(":", "").upper()

        ip = entry.get("ip_address", "")
        arp_table[mac] = ip
    if not arp_table:
        logging.error("Arp Table most likely empty")
    return arp_table


def create_mac_table(mac_data):
    mac_table = {}
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
    return mac_table


def create_lldp_table(lldp_data):
    lldp_table = {}
    if isinstance(lldp_data, list):
        for neighbor in lldp_data:
            remote_host = neighbor.get("neighbor", "")

            local_port = neighbor.get("local_interface", "")
            local_port = str(local_port)
            capabilities = neighbor.get("capabilities", "")
            is_network_device = any(cap in capabilities for cap in ["B", "R"])
            is_end_host = "S" in capabilities

            if remote_host and local_port:
                lldp_table[local_port] = {
                    "hostname": remote_host,
                    "is_network_device": is_network_device,
                    "is_end_host": is_end_host,
                    "capabilities": capabilities
                }
    return lldp_table


def local_switch(net_connect, detected_os, ip_address):
    """
    #######################################################################################
    Parse the detected OS to determine the local switch role and device type
    #######################################################################################
    """
    try:
           switch_name = net_connect.find_prompt().strip("#>")
    except Exception as e:
            logging.error(f"Could not read switch prompt: {e}")
            switch_name = None

    manufacturer = ""
    if detected_os in ["voss", "slx", "exos"]:
        manufacturer = "Extreme"
    elif detected_os == "cisco":
        manufacturer = "Cisco"

    role = "Core Switch"
    device_type = "Generic Switch"
    status = "active"
    site = nb_utils.get_site(ip_address)

    checks = {
        "name": switch_name,
        "site": site,
        "device_type": device_type,
        "role": role,
        "status": status,
    }
    missing = [k for k, v in checks.items() if not v]
    if missing:
        logging.error(
            f"Missing fields [{', '.join(missing)}] cannot upload local switch"
        )
        return None

    switch_info = {
        "name": switch_name,
        "site": {"name": site},
        "device_type": {"model": device_type},
        "role": {"name": role},
        "status": {"name": status},
        # "cf_ip_address": ip_address,############################################# UNCOMMENT when on real netbox
        # "cf_mac_address": mac_address,
        "description": f"Discovered via {detected_os or 'unknown'} OS fingerprint",
    }

    with open("output/local_switch.json", "w") as f:
        json.dump(switch_info, f, indent=4)
    logging.info(
        "Local switch parsed for netbox upload! Data saved to local_switch.json"
    )
    logging.debug(f"local switch dict: \n{switch_info}")
    return switch_info


def connected_devices(raw_data):
    """
    #######################################################################################
    Correlates ARP, MAC Table, and LLDP data to form json for nb import
    Will not work if TextFSM fails
    #######################################################################################
    """

    connected_devices = []

    arp_data = raw_data.get("show ip arp", [])
    arp_table = create_arp_table(arp_data)

    mac_data = raw_data.get("show mac address-table dynamic", [])
    mac_table = create_mac_table(mac_data)

    lldp_data = raw_data.get("show lldp neighbors detail", [])
    lldp_table = create_lldp_table(lldp_data)


    for mac, ports in mac_table.items():
        ip_address = arp_table.get(mac, "")
        site = nb_utils.get_site(ip_address)


        for port in ports:
            role = ""
            device_type = ""
            status = "active"
            name ="MAC ARP DISCOVERED"
            source="MAC_ARP"

            if port in lldp_table:
                lldp_info = lldp_table[port]
                name = lldp_info["hostname"]
                is_network_device = lldp_info["is_network_device"]
                source = "LLDP"

                # Determine Netbox Role via LLDP Capabilities flags
                if "R" in lldp_info["capabilities"]:
                    role = "Router"
                    device_type = "Generic Router"
                elif "B" in lldp_info["capabilities"]:
                    role = "Switch"
                    device_type = "Generic Switch"
                else:
                    role = "Endpoint"
                    device_type = "Unknown Enpoint"
            else:
                # Port has no LLDP neighbor. If it only has 1 dynamic MAC, it's likely a host workstation.
                role = "Endpoint"
                device_type = "Unknown Endpoint"
                name = f"Unknown Endpoint-{mac}"

            checks = {
                            "site": site,
                            "device_type": device_type,
                            "role": role,
                            "status": status
                        }

            missing = [k for k, v in checks.items() if not v]
            if not missing:
                device_info = {
                    "name": name,
                    "site": {"name": site},
                    "device_type": {"model": device_type},
                    "role": {"name": role},
                    "status": {"name": status},
                    "switch_port": port,
                    "cf_mac_address": ":".join([mac[i : i + 2] for i in range(0, 12, 2)]),
                    "cf_ip_address": ip_address,
                    "cf_installation_date": "1900-1-1",
                    "description": f"Discovered via {source} correlation",
                }
                logging.debug(f"Adding device: {device_info}")
                connected_devices.append(device_info)
            else:

                logging.error(
                    f"Missing Fields [{', '.join(missing)}]"
                    f"cannot upload device with ip: {ip_address}, port: {port}"
                )

    if connected_devices:
        with open("output/connected_devices.json", "w") as f:
            json.dump(connected_devices, f, indent=4)
        logging.info(
            "Connected Devices parsing successful! Data saved to connected_devices.json"
        )
    return connected_devices
