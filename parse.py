import json
import logging

from mac_vendor_lookup import MacLookup, VendorNotFoundError

import nb_utils

_mac_lookup = MacLookup()
logger = logging.getLogger(__name__)


def create_arp_table(arp_data):
    logger.debug(f"Arp data: {arp_data}")
    arp_table = {}
    for entry in arp_data:
        mac = entry.get("MAC", "")
        mac = str(mac).replace(".", "").replace(":", "").upper()

        ip = entry.get("IP", "")
        arp_table[mac] = ip
    if not arp_table:
        logger.error("Arp Table empty")
    logger.debug(f"Arp Table created: {arp_table}")
    return arp_table


def create_mac_table(mac_data, lldp_table):
    mac_table = {}
    for entry in mac_data:
        mac = entry.get("MAC", "")
        mac = str(mac).replace(".", "").replace(":", "").upper()

        port = entry.get("PORT", "")

        if mac and port:
            if port in mac_table:
                if mac in lldp_table:
                    mac_table[port] = mac
            else:
                mac_table[port] = mac
        logging.debug(f"Mapping {port} to {mac}")

    if not mac_table:
        logger.error("Mac Table empty")
    logger.debug(f"Mac Table created: {mac_table}")
    return mac_table


def create_lldp_table(lldp_data):
    lldp_table = {}
    if isinstance(lldp_data, list):
        for neighbor in lldp_data:
            remote_host = neighbor.get("HOSTNAME", "").split(".")[0].strip().lower()
            chassis = str(neighbor.get("CHASSIS_ID", ""))
            chassis = ":".join([chassis[i : i + 2] for i in range(0, 12, 2)])

            remote_port = neighbor.get("REMOTE_PORT", "NIC")

            capabilities = neighbor.get("ENABLED_CAPABILITIES", "")
            is_switch = any(cap in capabilities for cap in ["B", "Bridge"])
            is_router = any(cap in capabilities for cap in ["R", "Router"])

            if remote_host and chassis:
                lldp_table[chassis] = {
                    "hostname": remote_host,
                    "capabilities": capabilities,
                    "remote_port": remote_port,
                }
            if is_switch:
                lldp_table[chassis]["role"] = "Switch"
                lldp_table[chassis]["device_type"] = "Unknown Switch"
            elif is_router:
                lldp_table[chassis]["role"] = "Router"
                lldp_table[chassis]["device_type"] = "Unknown Router"
            else:
                lldp_table[chassis]["role"] = "Endhost"
                lldp_table[chassis]["device_type"] = "Unknown Likely Endhost"

    if not lldp_table:
        logger.warning("LLDP table empty connected devices may be vague")
    logger.debug(f"LLDP table created: {lldp_table}")
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


def get_manufacturer(mac_address):
    """
    Looks up the vendor for a MAC address using a single shared MacLookup
    instance. Returns None if the vendor can't be determined instead of
    raising, so one unknown MAC doesn't abort the whole device list.
    """
    try:
        return _mac_lookup.lookup(mac_address)
    except VendorNotFoundError:
        logger.debug(f"No known vendor for MAC '{mac_address}'")
        return None
    except Exception as e:
        logger.warning(f"MAC vendor lookup failed for '{mac_address}': {e}")
        return None


def local_switch(net_connect, switch_info, ip_address, os_template, test=False):
    """
    #######################################################################################
    Parse the detected OS to determine the local switch role and device type
    #######################################################################################
    """

    logger.info("Parsing local switch for netbox...")

    try:
        switch_name = net_connect.find_prompt().strip("#> ")
    except Exception as e:
        logger.error(f"Could not read switch prompt: {e}")
        switch_name = None

    switch_parsed = {}

    try:
        role = "Switch"
        device_type = switch_info["MODEL"]
        status = "active"
        site = ""
        ports = parse_ports(switch_info["ports"])
        serial = switch_info.get("SERIAL", "")
        manufacturer = get_manufacturer(switch_info["MAC"])

        if test:
            site = "Test Site Beta"
            logger.info(f"TEST UPLOAD DETECTED SETTING SITE TO: '{site}'")
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
            logger.error(
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
            logger.info(
                f"Local switch parsed for netbox upload! Data saved to output/{ip_address}_local_switch.json"
            )
        except Exception as e:
            logger.warning(
                f"Could not create parsed for nb upload json make sure output folder is in project Reason: {e}"
            )
    except Exception as e:
        logger.error(f"Unable to parse local switch for netbox Reason: {e}")
        raise Exception(e)
    return switch_parsed


def connected_devices(raw_data, switch_ip, test=False):
    """
    #######################################################################################
    Correlates ARP, MAC Table, and LLDP data to form json for nb import
    Will not work if TextFSM fails
    #######################################################################################
    """

    logger.info("Parsing connected devices for netbox...")
    connected_devices = []

    try:
        arp_data = raw_data.get("arp", [])
        arp_table = create_arp_table(arp_data)

        mac_data = raw_data.get("mac", [])
        lldp_data = raw_data.get("lldp", [])
        lldp_table = create_lldp_table(lldp_data)
        mac_table = create_mac_table(mac_data, lldp_table)

        no_touch = set()
        for port, mac in mac_table.items():
            ip_address = arp_table.get(mac, "")
            manufacturer = get_manufacturer(
                ":".join([mac[i : i + 2] for i in range(0, 12, 2)])
            )
            if test:
                site = "Test Site Beta"
                logger.info(f"TEST UPLOAD DETECTED SETTING SITE TO: '{site}'")
            else:
                site = nb_utils.get_site(ip_address)

                # for port in ports:
                # Check if we added something by lldp and if we did  it is mostlikely a uplink with multiple macs on it so no touch
                if port in no_touch:
                    continue
            role = ""
            device_type = ""
            status = "active"
            name = "UNKNOWN DISCOVERED DEVICE"
            source = "MAC_ARP"
            remote_interface = "eth0"

            if mac in lldp_table:
                no_touch.add(port)
                lldp_info = lldp_table[mac]
                name = lldp_info["hostname"]
                remote_interface = lldp_info["remote_port"] or "eth0"
                role = lldp_info.get("role", "")
                device_type = lldp_info.get("device_type", "UNKNOWN")
                source = "LLDP"

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
                if manufacturer:
                    device_info["manufacturer"] = {"name": manufacturer}
                    logger.debug(f"Adding device: {device_info}")
                    connected_devices.append(device_info)
            else:
                logger.error(
                    f"Missing Fields [{', '.join(missing)}]"
                    f"cannot upload device with ip: {ip_address}, port: {port}"
                )
        try:
            if connected_devices:
                with open(f"output/{switch_ip}_connected_devices.json", "w") as f:
                    json.dump(connected_devices, f, indent=4)
                logger.info(
                    f"Connected Devices parsing successful! Data saved to output/{switch_ip}_connected_devices.json"
                )
        except Exception as e:
            raise Exception(
                f"Unable to create output json for local switch make sure you have output folder in project: {e}"
            )

    except Exception as e:
        logger.error(e)
    return connected_devices
