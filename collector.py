import json
import logging

from netmiko import redispatch

import textfsm
import io

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
        raw_output = ssh_session.send_command("show version")
        int_output = ssh_session.send_command("show interfaces status")
        # logging.debug(f"SHOW VERSION OUTPUT:\n{raw_output}")
        # logging.debug(f"SHOW INT BRIEF OUTPUT:\n {int_output}")
        clean_dict = {}


        if "cisco" in raw_output:
            logging.info("OS fingerprint match: Cisco.  Redispatching...")
            redispatch(ssh_session, device_type="cisco_ios")
            logging.debug("Redispatch Succesfull! Extracting switch device info...")
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

            logging.debug(f"Switch info extracted with textFSM: \n {clean_dict}")

            return clean_dict

        elif "ExtremeXOS" in raw_output:
            logging.info("OS fingerprint match: EXOS.  Redispatching...")
            redispatch(ssh_session, device_type="extreme_exos")
            return "exos"
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
        return None
    except Exception as e:
        logging.error(f"{e}")


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
