import json
import logging

from netmiko import redispatch

import textfsm
import io


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
        os_name = ""
        for os in os_templates.keys():
            if os in raw_output:
                logging.info(f"OS fingerprint match: {os}.  Redispatching...")
                os_name = os
        if os_name == "":
            raw_output = ssh_session.send_command("show switch", expect_string=r"#\s*$")
            for os in os_templates.keys():
                if os in raw_output:
                    logging.info(f"OS fingerprint match: {os}.  Redispatching...")
                    os_name = os
        elif os_name == "":
            logging.error("SWITCH OPERATING SYSTEM NOT DETECTED -> make sure the name is correct in os_templates.json as that is what is searched for")
            return clean_dict
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
             logging.debug(f"PORTS FOUND: {parsed_ports}")
             if parsed_ports:
                 clean_dict["ports"] = parsed_ports
             logging.info("Switch data collection successful!")
             logging.debug(f"switch data collected: {clean_dict}")
             return clean_dict

        except Exception as e:
             logging.error(f"Redispatch failed reason: {e}")

    except Exception as e:
        logging.error(f"{e}")
    return clean_dict


def get_device_data(ssh_session, os_templates, os_name, switch_ip):
    """
    ###############################################################
    Accepts an active ssh connection the os template of the oper
    Runs the list of commands
    Returns big textFSM dict with commands as key and value as the dict generated from the command
    ###############################################################
    """

    output = {}
    parsed_lldp = None
    os_template = os_templates.get(os_name)

    logging.info(f"Getting connected devices info from {os_name} switch...")
    try:
        arp_cmd = os_template.get("arp_command")
        arp_template = f"config/custom_templates/{os_name}/{os_template.get("textfsm_templates").get("arp")}"

        mac_cmd = os_template.get("mac_command")
        mac_template = f"config/custom_templates/{os_name}/{os_template.get("textfsm_templates").get("mac")}"

        lldp_cmd = os_template.get("lldp_command")
        lldp_template = f"config/custom_templates/{os_name}/{os_template.get("textfsm_templates").get("lldp")}"

        try:
            arp_output = ssh_session.send_command(arp_cmd)
            with open(arp_template, mode='r', newline='') as f:
                arp_template = f.read()
            temp_file = io.StringIO(arp_template)
            arp_parse = textfsm.TextFSM(temp_file)
            parsed_arp = arp_parse.ParseTextToDicts(arp_output)
            logging.info("Arp extraction successful!")
            logging.debug(f"Arp data: {parsed_arp}")
        except Exception as e:
            logging.error(f"Arp data not extracted(check arp textfsm template) reason: {e}")
            raise Exception("arp extraction failed")

        try:
            mac_output = ssh_session.send_command(mac_cmd)
            with open(mac_template, mode='r', newline='') as f:
                mac_template = f.read()
            temp_file = io.StringIO(mac_template)
            mac_parse = textfsm.TextFSM(temp_file)
            parsed_mac = mac_parse.ParseTextToDicts(mac_output)
            logging.info("Mac Table extraction successful!")
            logging.debug(f"Mac Table: {parsed_mac}")
        except Exception as e:
            logging.error(f"mac table data not extracted(check mac table textfsm template) reason: {e}")
            raise Exception("mac table extraction failed")

        try:
            lldp_output = ssh_session.send_command(lldp_cmd)
            with open(lldp_template, mode='r', newline='') as f:
                lldp_template = f.read()
            temp_file = io.StringIO(lldp_template)
            lldp_parse = textfsm.TextFSM(temp_file)
            parsed_lldp = lldp_parse.ParseTextToDicts(lldp_output)
            logging.info("LLDP data extraction successful!")
            logging.debug(f"LLDP data: {parsed_lldp}")
        except Exception as e:
            logging.warning(f"lldp data not extracted(check lldp textfsm template) reason: {e}")
            logging.warning("Data will not be as accurate without lldp data as it will have to assume all connected devices are unknown endpoints")

        output["arp"] = parsed_arp
        output["mac"] = parsed_mac
        if(parsed_lldp):
            output["lldp"] = parsed_lldp


        with open(f"output/{switch_ip}_raw_output.json", mode="w") as f:
            json.dump(output, f)
            logging.info(f"Conneceted devices collected succesfully! data saved to output/{switch_ip}_raw_output.json")
    except Exception as e:
        logging.error(f"Could not collect data from templates. Reason: {e}")

    return output
