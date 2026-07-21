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
        logging.debug("switch parsed working on ports...")

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


def get_switch_data(ssh_session):

    """
    #######################################################################################
    Accepts an active ssh connection
    Probes the output of show version for what is contained in the output
    Will change the os on the ssh connection if a version is connected.
    Returns the textFSM dict
    #######################################################################################
    """
    try:
        logging.info("Detecting OS...")
        raw_output = ssh_session.send_command("show version", expect_string=r"#\s*$")
        clean_dict = {}


        if "cisco" in raw_output:
            logging.info("OS fingerprint match: Cisco.  Redispatching...")
            redispatch(ssh_session, device_type="cisco_ios")
            logging.info("Redispatch Succesfull! Extracting switch device info...")

            clean_dict = get_cisco_data(ssh_session, raw_output) #uses the raw ouput because cisco is cool
            logging.debug(f"Switch info collected: \n {clean_dict}")

            return clean_dict

        elif any(system in raw_output for system in ["ExtremeXOS", "EXOS", "Switch Engine", "exos"]):
            logging.info("OS fingerprint match: EXOS.  Redispatching...")
            redispatch(ssh_session, device_type="extreme_exos")
            logging.info("Redispatch Succesfull! Extracting switch device info...")

            clean_dict = get_exos_data(ssh_session) # has its own commands to run for outputs because extreme stinks
            logging.debug(f"Switch info collected: {clean_dict}")
            return clean_dict

        elif "SLX" in raw_output:
            logging.info("OS fingerprint match: SLX-OS. Redispatching...")
            redispatch(ssh_session, device_type="extreme_slx")
            return "slx"
        elif "Invalid input" in raw_output:
            voss_probe = ssh_session.send_command("show sys-info")
            if "Invalid input" not in voss_probe:
                logging.info("OS fingerprint match: VOSS Redispatching...")
                redispatch(ssh_session, device_type="extreme_vsp")
                return "voss"

        logging.error("OS detetcion failed no fingerprints matched")

    except Exception as e:
        logging.error(f"{e}")
    return {"OS": "Unknown"}


def get_device_data(net_connect, commands: list):
    """
    ###############################################################
    Accepts an active ssh connection and commands to run
    Runs the list of commands
    Returns big textFSM dict with commands as key and value as the dict generated from the command
    ###############################################################
    """

    outputs_dict = {}

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
                    f"'{command}' not parsed reason: {outputs_dict[command].get('raw_output')} \n continuing... "
                )

        except Exception as e:
            logging.error(f"Command output was unexpected check syntax: {e}")

    if outputs_dict:
        with open("output/raw_output.json", "w") as f:
            json.dump(outputs_dict, f, indent=4)
        logging.info(
            "Raw command data collecting succesful! Raw output data is saved to raw_output.json"
        )
    else:
        logging.error("No raw output generated check commands")

    return outputs_dict
