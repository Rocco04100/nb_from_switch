import json
import logging

from netmiko import ConnectHandler

import detect


def get_switch(net_connect):
    logging.info("Collecting and cleaning switch data for netbox import")
    try:
        switch_name = net_connect.find_prompt().strip("#>")
        detected_os = detect.operating_system(net_connect)
        if detected_os in ["voss", "slx", "exos"]:
            manufacturer = "Extreme"
        else:
            manufacturer = ""
    except Exception as e:
        logging.error(e)

    local_switch = {
        "role": 14,
        "name": switch_name,
        "site": 2,
        "device_type": 19,
    }

    if manufacturer:
        local_switch["manufacturer"] = manufacturer

    with open("output/local_switch.json", "w") as f:
        json.dump(local_switch, f, indent=4)
    logging.info(
        "Switch data collected and cleaned for netbox! Data saved to local_switch.json"
    )
    logging.debug(local_switch)
    return local_switch


def get_data(net_connect, commands: list):
    """
    ###############################################################
    - Outputs a dictionary of raw data from a command using TextFSM
    - Needs the switch to run it on and the commands we will be running
    - Data is not clean for netbox so need to use parse in main
    - Will abort if the operating system is not properly detected
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
