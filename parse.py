import json
import logging
from sre_parse import parse_template

from mac_vendor_lookup import MacLookup

import nb_utils


def create_arp_table(arp_data):
    logging.debug(f"Arp data: {arp_data}")
    arp_table = {}
    for entry in arp_data:
        mac = entry.get("MAC", "")
        mac = str(mac).replace(".", "").replace(":", "").upper()

        ip = entry.get("IP", "")
        arp_table[mac] = ip
    if not arp_table:
        logging.error("Arp Table empty")
    logging.debug(f"Arp Table created: {arp_table}")
    return arp_table


def create_mac_table(mac_data):
    mac_table = {}
    for entry in mac_data:
        mac = entry.get("MAC", "")
        if isinstance(mac, list):
            mac = mac[0] if mac else ""
        mac = str(mac).replace(".", "").replace(":", "").upper()

        port = entry.get("PORT", "")
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

    if not mac_table:
        logging.error("Mac Table empty")
    logging.debug(f"Mac Table created: {mac_table}")
    return mac_table


def create_lldp_table(lldp_data):
    lldp_table = {}
    if isinstance(lldp_data, list):
        for neighbor in lldp_data:
            remote_host = neighbor.get("HOSTNAME", "").split(".")[0].strip().lower()
            local_port = str(neighbor.get("LOCAL_PORT", ""))

            remote_port = neighbor.get("REMOTE_PORT", "NIC")

            capabilities = neighbor.get("ENABLED_CAPABILITIES", "")
            is_switch = any(cap in capabilities for cap in ["B", "Bridge"])
            is_router = any(cap in capabilities for cap in ["R", "Router"])

            if remote_host and local_port:
                lldp_table[local_port] = {
                    "hostname": remote_host,
                    "capabilities": capabilities,
                    "remote_port": remote_port,
                }
            if is_switch:
                lldp_table[local_port]["role"] = "Switch"
                lldp_table[local_port]["device_type"] = "Unknown Switch"
            elif is_router:
                lldp_table[local_port]["role"] = "Router"
                lldp_table[local_port]["device_type"] = "Unknown Router"
            else:
                lldp_table[local_port]["role"] = "Endhost"
                lldp_table[local_port]["device_type"] = "Unknown Likely Endhost"

    if not lldp_table:
        logging.warning("LLDP table empty connected devices may be vague")
    logging.debug(f"LLDP table created: {lldp_table}")
    return lldp_table


def parse_ports(ports):
    # Determine if we need to skip the header row ("Port")
    start_index = 1 if ports and ports[0].get("PORT") == "Port" else 0

    for item in ports[start_index:]:
        # Standardize the speed types
        # if "10/100/1000BaseTX" in item["type"]:
        #     item["type"] = "1000base-tx)"
        # elif "SFP" in item["type"]:
        #     item["type"] = "1000base-x-sfp"
        item["TYPE"] = "other"

    return ports


def local_switch(net_connect, switch_info, ip_address, os_template, test=False):
    """
    #######################################################################################
    Parse the detected OS to determine the local switch role and device type
    #######################################################################################
    """

    logging.info("Parsing local switch for netbox...")

    try:
        switch_name = net_connect.find_prompt().strip("#> ")
    except Exception as e:
        logging.error(f"Could not read switch prompt: {e}")
        switch_name = None

    switch_parsed = {}

    try:
        role = "Switch"
        device_type = switch_info["MODEL"]
        status = "active"
        site = ""
        ports = parse_ports(switch_info["ports"])
        serial = switch_info.get("SERIAL", "")
        manufacturer = MacLookup().lookup(switch_info["MAC"])
        if test:
            site = "Test Site Beta"
            logging.info(f"TEST UPLOAD DETECTED SETTING SITE TO: '{site}'")
        else:
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

        switch_parsed = {
            "name": switch_name,
            "site": {"name": site},
            "device_type": {"model": device_type},
            "role": {"name": role},
            "status": status,
            # "cf_ip_address": ip_address,############################################# UNCOMMENT when on real netbox
            "cf_mac_address": switch_info["MAC"],
            "description": f"Info from script -> | mac:{switch_info['MAC']} | OS:{switch_info['OS']}",
            "_ports": ports,
        }
        if serial:
            switch_parsed["serial"] = serial
        if manufacturer:
            switch_parsed["manufacturer"] = {"name": manufacturer}
        try:
            with open(f"output/{ip_address}_local_switch.json", "w") as f:
                json.dump(switch_parsed, f, indent=4)
            logging.info(
                f"Local switch parsed for netbox upload! Data saved to output/{ip_address}_local_switch.json"
            )
        except Exception as e:
            logging.warning(
                f"Could not create parsed for nb upload json make sure output folder is in project Reason: {e}"
            )
    except Exception as e:
        logging.error(f"Unable to parse local switch for netbox Reason: {e}")
        raise Exception(e)
    return switch_parsed


def connected_devices(raw_data, switch_ip, test=False):
    """
    #######################################################################################
    Correlates ARP, MAC Table, and LLDP data to form json for nb import
    Will not work if TextFSM fails
    #######################################################################################
    """

    logging.info("Parsing connected devices for netbox...")
    connected_devices = []

    try:
        arp_data = raw_data.get("arp", [])
        arp_table = create_arp_table(arp_data)

        mac_data = raw_data.get("mac", [])
        mac_table = create_mac_table(mac_data)

        lldp_data = raw_data.get("lldp", [])
        lldp_table = create_lldp_table(lldp_data)

        for mac, ports in mac_table.items():
            ip_address = arp_table.get(mac, "")
            if test:
                site = "Test Site Beta"
                logging.info(f"TEST UPLOAD DETECTED SETTING SITE TO: '{site}'")
            else:
                site = nb_utils.get_site(ip_address)
            for port in ports:
                role = ""
                device_type = ""
                status = "active"
                name = "UNKNOWN DISCOVERED DEVICE"
                source = "MAC_ARP"
                remote_interface = "eth0"

                if port in lldp_table:
                    lldp_info = lldp_table[port]
                    name = lldp_info["hostname"]
                    remote_interface = lldp_info["remote_port"] or "eth0"
                    role = lldp_info.get("role", "")
                    device_type = lldp_info.get("device_type", "UNKNOWN")
                else:
                    # Port has no LLDP neighbor. If it only has 1 dynamic MAC, it's likely a host workstation.
                    role = "Unknown"
                    device_type = "Unknown"
                    name = f"Unknown Host({':'.join([mac[i : i + 2] for i in range(0, 12, 2)])})"

                checks = {
                    "site": site,
                    "device_type": device_type,
                    "role": role,
                    "status": status,
                }

                missing = [k for k, v in checks.items() if not v]
                if not missing:
                    device_info = {
                        "name": name,
                        "site": {"name": site},
                        "device_type": {"model": device_type},
                        "manufacturer": {
                            "name": MacLookup().lookup(
                                ":".join([mac[i : i + 2] for i in range(0, 12, 2)])
                            )
                        },
                        "role": {"name": role},
                        "status": status,
                        # "switch_port": port,
                        "cf_mac_address": ":".join(
                            [mac[i : i + 2] for i in range(0, 12, 2)]
                        ),
                        # "cf_ip_address": ip_address,
                        # "cf_installation_date": "1900-1-1",
                        "description": f"Discovered via {source} correlation",
                        "_local_interface": port,  # the switch's port name
                        "_remote_interface": remote_interface,  # the device's own port name (or "NIC")
                        "_ip_address": ip_address,
                    }
                    logging.debug(f"Adding device: {device_info}")
                    connected_devices.append(device_info)
                else:
                    logging.error(
                        f"Missing Fields [{', '.join(missing)}]"
                        f"cannot upload device with ip: {ip_address}, port: {port}"
                    )
        try:
            if connected_devices:
                with open(f"output/{switch_ip}_connected_devices.json", "w") as f:
                    json.dump(connected_devices, f, indent=4)
                logging.info(
                    f"Connected Devices parsing successful! Data saved to output/{switch_ip}_connected_devices.json"
                )
        except Exception as e:
            raise Exception(
                f"Unable to create output json for local switch make sure you have output folder in project: {e}"
            )

    except Exception as e:
        logging.error(e)
    return connected_devices
