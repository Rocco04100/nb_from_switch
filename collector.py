import json
import logging

from netmiko import redispatch

import textfsm
import io

def get_exos_data(ssh_session):
    clean_dict ={}
    switch_output = ssh_session.send_command("show switch")
    with open('custom_templates/exos_switch.textfsm', mode='r', newline='') as f:
        switch_template = f.read()
    temp_file = io.StringIO(switch_template)
    switch_parse = textfsm.TextFSM(temp_file)
    parsed_switch = switch_parse.ParseTextToDicts(switch_output)

    if parsed_switch:
        clean_dict = parsed_switch[0]
        clean_dict["OS"] = "exos"
        logging.debug("Switch colleceted working on ports...")

    port_output = ssh_session.send_command("show ports no-refresh")
    with open('custom_templates/exos_ports.textfsm', mode='r', newline='') as f:
        ports_template = f.read()
    temp_file = io.StringIO(ports_template)
    ports_parse = textfsm.TextFSM(temp_file)
    parsed_ports = ports_parse.ParseTextToDicts(port_output)

    if parsed_ports:
        clean_dict["ports"] = parsed_ports
    return clean_dict


def get_cisco_data(ssh_session, raw_output):
    clean_dict = {}
    int_output = ssh_session.send_command("show interfaces status")
    with open('custom_templates/cisco_version.textfsm', mode='r', newline='') as f:
        version_template = f.read()
    with open('custom_templates/cisco_interface.textfsm', mode='r', newline='') as f:
        interface_template = f.read()

    template_file_like = io.StringIO(version_template)
    int_file_like = io.StringIO(interface_template)
    fsm_engine = textfsm.TextFSM(template_file_like)
    parse_port = textfsm.TextFSM(int_file_like)
    parsed_info = fsm_engine.ParseText(raw_output)
    parsed_ports = parse_port.ParseTextToDicts(int_output)

    if parsed_info:
        clean_dict.update(zip(fsm_engine.header, parsed_info[0]))

    clean_dict["OS"] = "cisco_ios"
    clean_dict["ports"] = parsed_ports
    return clean_dict



def get_switch_data(ssh_session, os_templates):

    """
    #######################################################################################
    Accepts an active ssh connection
    Probes the output of show version for what is contained in the output
    Will change the os on the ssh connection if a version is connected.
    Returns the textFSM dict
    #######################################################################################
    """
    clean_dict = {}
    try:
        logging.info("Detecting OS...")
        raw_output = ssh_session.send_command("show version", expect_string=r"#\s*$")
        for os_name in os_templates.keys():
            if os_name in raw_output:
                logging.info(f"OS fingerprint match: {os_name}.  Redispatching...")

                try:
                    os_template = os_templates.get(os_name)
                    netmiko_type = os_template.get("device_type")
                    redispatch(ssh_session, device_type=netmiko_type)
                    logging.info("Redispatch Successful! Extracting switch device info...")

                    version_cmd = os_template.get("version_command")
                    version_textfsm = f"config/custom_templates/{os_name}/{os_template.get("textfsm_templates").get("version")}"
                    switch_output = ssh_session.send_command(version_cmd)

                    if switch_output:
                        with open(version_textfsm, mode='r', newline='') as f:
                            template = f.read()
                        temp_file = io.StringIO(template)
                        switch_parse = textfsm.TextFSM(temp_file)
                        parsed_switch = switch_parse.ParseTextToDicts(switch_output)
                        clean_dict = parsed_switch[0]
                        clean_dict["OS"] = os_name

                    ports_cmd = os_template.get("ports_command")
                    ports_textfsm = f"config/custom_templates/{os_name}/{os_template.get("textfsm_templates").get("ports")}"

                    port_output = ssh_session.send_command(ports_cmd)
                    with open(ports_textfsm, mode='r', newline='') as f:
                        ports_template = f.read()
                    temp_file = io.StringIO(ports_template)
                    ports_parse = textfsm.TextFSM(temp_file)
                    parsed_ports = ports_parse.ParseTextToDicts(port_output)
                    if parsed_ports:
                        clean_dict["ports"] = parsed_ports
                    logging.info("Switch data collection successful!")
                    logging.debug(f"switch data collected: {clean_dict}")
                    return clean_dict

                except Exception as e:
                    logging.error(f"Redispatch failed reason: {e}")

    #     if "cisco" in raw_output:
    #         logging.info("OS fingerprint match: Cisco.  Redispatching...")
    #         redispatch(ssh_session, device_type="cisco_ios")
    #         logging.info("Redispatch Succesfull! Extracting switch device info...")

    #         clean_dict = get_cisco_data(ssh_session, raw_output) #uses the raw ouput because cisco is cool
    #         logging.debug(f"Switch info collected: \n {clean_dict}")

    #         return clean_dict

    #     elif any(system in raw_output for system in ["ExtremeXOS", "EXOS", "Switch Engine", "exos"]):
    #         logging.info("OS fingerprint match: EXOS.  Redispatching...")
    #         redispatch(ssh_session, device_type="extreme_exos")
    #         logging.info("Redispatch Succesfull! Extracting switch device info...")

    #         clean_dict = get_exos_data(ssh_session) # has its own commands to run for outputs because extreme stinks
    #         logging.debug(f"Switch info collected: {clean_dict}")
    #         return clean_dict

    #     elif "SLX" in raw_output:
    #         logging.info("OS fingerprint match: SLX-OS. Redispatching...")
    #         redispatch(ssh_session, device_type="extreme_slx")
    #         return "slx"
    #     elif "Invalid input" in raw_output:
    #         voss_probe = ssh_session.send_command("show sys-info")
    #         if "Invalid input" not in voss_probe:
    #             logging.info("OS fingerprint match: VOSS Redispatching...")
    #             redispatch(ssh_session, device_type="extreme_vsp")
    #             return "voss"

    #     logging.error("OS detetcion failed no fingerprints matched")

    except Exception as e:
        logging.error(f"{e}")
    return clean_dict


def get_device_data(ssh_session, detected_os):
    """
    ###############################################################
    Accepts an active ssh connection and commands to run
    Runs the list of commands
    Returns big textFSM dict with commands as key and value as the dict generated from the command
    ###############################################################
    """

    outputs_dict = {}
    if (detected_os == "exos"):
        outputs_dict = get_exos_devices(ssh_session)
    elif detected_os == "cisco_ios":
        outputs_dict = get_cisco_devices(ssh_session)

    if outputs_dict:
        with open("output/raw_output.json", "w") as f:
            json.dump(outputs_dict, f, indent=4)
        logging.info(
            "Raw command data collecting succesful! Raw output data is saved to raw_output.json"
        )
    else:
        logging.error("No raw output generated check commands")

    return outputs_dict


def get_exos_devices(ssh_session):

    output = {}
    logging.info("Getting connected device info from exos switch...")
    iparp_output = ssh_session.send_command("show iparp")
    with open('custom_templates/exos_iparp.textfsm', mode='r', newline='') as f:
        iparp_template = f.read()
    temp_file = io.StringIO(iparp_template)
    iparp_parse = textfsm.TextFSM(temp_file)
    parsed_iparp = iparp_parse.ParseTextToDicts(iparp_output)

    fdb_output = ssh_session.send_command("show fdb")
    with open('custom_templates/exos_fdb.textfsm', mode='r', newline='') as f:
        fdb_template = f.read()
    temp_file = io.StringIO(fdb_template)
    fdb_parse = textfsm.TextFSM(temp_file)
    parsed_fdb = fdb_parse.ParseTextToDicts(fdb_output)

    lldp_output = ssh_session.send_command("show lldp")
    with open('custom_templates/exos_lldp.textfsm', mode='r', newline='') as f:
        lldp_template = f.read()
    temp_file = io.StringIO(lldp_template)
    lldp_parse = textfsm.TextFSM(temp_file)
    parsed_lldp = lldp_parse.ParseTextToDicts(lldp_output)

    output["show iparp"] = parsed_iparp
    output["show fdb"] = parsed_fdb
    output["show lldp neighbors details"] = parsed_lldp

    return output


def get_cisco_devices(ssh_session):
    commands = [
        # "show version",
        # "show interfaces",
        # "show ip interface brief",
        # "show interface status",
        "show ip arp",  # Maps IP -> MAC
        "show mac address-table dynamic",  # Maps MAC -> Port
        "show lldp neighbors detail",  # Identifies Network Devices
    ]
    outputs_dict = {}
    for command in commands:
        try:
            output = ssh_session.send_command(
                command, read_timeout=30, use_textfsm=True
            )
            if isinstance(output, list):
                logging.info(f"--- {command} (Parsed) ---")
                outputs_dict[command] = output
            else:
                logging.info(f"--- {command} (Raw) ---")
                # if text is not parsed it still adds raw output but flags it with COMMAND NOT PARSED
                outputs_dict[command] = {
                    "COMMAND NOT PARSED": command,
                    "raw_output": output,
                }

                logging.error(
                    f"'{command}' not parsed raw output for debug: {outputs_dict[command].get('raw_output')} \n continuing... "
                )

        except Exception as e:
            logging.error(f"Command output was unexpected check syntax: {e}")
    return outputs_dict
