import logging
import textfsm
import io

from netmiko import redispatch


def operating_system(ssh_session):

    """
    #######################################################################################
    Accepts an active ssh connection
    Probes the ouuput of show version for what is contained in the output
    Will change the os on the ssh connection if a version is connected.
    Returns the os in a string for use in other functions
    #######################################################################################
    """
    try:
        logging.info("Detecting OS...")
        raw_output = ssh_session.send_command("show version")
        clean_dict = {}


        if "cisco" in raw_output:
            logging.info("OS fingerprint match: Cisco.  Redispatching...")
            redispatch(ssh_session, device_type="cisco_ios")
            logging.debug("Redispatch Succesfull! Extracting switch device info...")
            with open('custom_templates/cisco_version.textfsm', mode='r', newline='') as f:
                custom_template = f.read()

            template_file_like = io.StringIO(custom_template)
            fsm_engine = textfsm.TextFSM(template_file_like)
            parsed_rows = fsm_engine.ParseText(raw_output)

            clean_dict = dict(zip(fsm_engine.header, parsed_rows[0]), OS="cisco_ios")

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
