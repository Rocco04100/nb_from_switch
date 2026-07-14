import json
import logging


def create_arp_table(arp_data):
    arp_table = {}
    for entry in arp_data:
        mac = entry.get("mac_address", "")
        mac = str(mac).replace(".", "").replace(":", "").upper()

        ip = entry.get("ip_address", "")
        arp_table[mac] = ip

        if mac and ip != "Incomplete":
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
            if isinstance(remote_host, list):
                remote_host = remote_host[0] if remote_host else ""

            local_port = neighbor.get("local_interface", "")
            if isinstance(local_port, list):
                local_port = local_port[0] if local_port else ""
            local_port = str(local_port)

            if remote_host and local_port:
                lldp_table[local_port] = {
                    "hostname": remote_host,
                    "is_network_device": True,
                }
    return lldp_table


def connected_devices(raw_data):
    """
    #######################################################################################
    Correlates ARP, MAC Table, and LLDP data to form json for nb import
    Will not work if TextFSM fails
    #######################################################################################
    """

    connected_devices = []

    # -----------------------------------------------------------------
    # 1. Build Lookup Dictionaries
    # Build dict to look up MAC -> IP dict (from show ip ARP)
    # ----------------------------------------------------------------

    arp_data = raw_data.get("show ip arp", [])
    arp_table = create_arp_table(arp_data)

    # ----------------------------------------------------------------
    # Building MAC -> Interface dict (from MAC Address Table)
    # ----------------------------------------------------------------

    mac_data = raw_data.get("show mac address-table dynamic", [])
    mac_table = create_mac_table(mac_data)

    # -----------------------------------------------------------------------
    # 2. Process LLDP Neighbors
    # ------------------------------------------------------------------------

    lldp_data = raw_data.get("show lldp neighbors detail", [])
    lldp_table = create_lldp_table(lldp_data)

    # ------------------------------------------------------------------------
    # 3. Correlate all look up tables to build Final List
    # ------------------------------------------------------------------------

    moa_site_table = {
        "10.132": "BFCT",
        "10.135": "Braintree_Lex",
        # "10.2": "Building 2", -> No ip's in nb unsure
        "10.3": "Building 3",
        "10.4": "Building 4",
        # "10.5": "Buidling 5", -> No devices on nb unsure
        "10.6": "Building 6",
        "10.7": "Building 7",
        "10.8": "Building 8",
        "10.10": "Building 10",
        "10.11": "Building 11",
        # "10.53": "Building 16", -> Weird ip ask question
        "10.18": "Building 18",
        "10.19": "Building 19",
        # 20-24 are term c
        "10.20": "Building 20",  # some dpips are on 10.21 in building 20 its weird probably need another octect to specify
        "10.21": "Building 21",  # im guessing those dpips in bdlg 20 with 10.21 are in the wrong site
        "10.22": "Building 22",
        "10.23": "Building 23",
        "10.24": "Building 24",  # theres a vps switch on 10.31 wierd
        "10.25": "Building 25",
        # "10.26": "Building 26", -> No building 26 maybe under alias?
        # 27-29 are term b
        "10.27": "Building 27",
        "10.28": "Building 28",  # no objects yet
        "10.29": "Building 29",
        #        "10.30": "Building 30", -> No building 30 maybe under alias?
        # 31-32 are term a
        "10.31": "Building 31",
        "10.32": "Building 32",
        "10.44": "Building 44",
        "10.45": "Building 45",
        # "10.51": "Building 51", -> only has acs in netbox
        #
        # "10.52": "Building 52", -> only has acs in netbox
        "10.53": "Building 53",
        "10.55": "Building 55",
        "10.58": "Building 58",  # mostly acs in netbox
        "10.60": "Building 60",
        "10.61": "Building 61",
        "10.66": "Building 66",
        "10.72": "Builidng 72",
        "10.75": "Building 75",
        "10.76": "Building 76",
        "10.78": "Building 78",
        "10.79": "Building 79",
        "10.81": "Builidng 81",
        "10.91": "Building 91",
        "10.96": "Building 96",
        "10.100": "Building 100",
        "10.129": "Conley Shipyard",
        # "10.128": "FP East", I got no idea if there are different subnets
        # "10.128": "FP West"
        # "10.135": "Framingham Garage", this is parking network not moa_site_table
    }

    for mac, ports in mac_table.items():
        ip_address = arp_table.get(mac, None)

        if ip_address is None:
            logging.warn(f"MAC {mac} found in MAC table but NOT in ARP table")

        for port in ports:
            device_info = {
                "switch_port": port,
                "mac_address": ":".join([mac[i : i + 2] for i in range(0, 12, 2)]),
                "ip_address": ip_address,
                "hostname": None,
                "is_network_device": False,
                "source": "MAC_ARP_CORRELATION",
            }
            # if device_info["ip_address"] -> site logic soon

            if port in lldp_table:
                device_info["hostname"] = lldp_table[port]["hostname"]
                device_info["is_network_device"] = True
                device_info["source"] = "LLDP"

            connected_devices.append(device_info)
    if connected_devices:
        with open("output/connected_devices.json", "w") as f:
            json.dump(connected_devices, f, indent=4)
        logging.info(
            "\nConnected Devices parsing successful! Data saved to connected_devices.json"
        )
    return connected_devices
