import logging

from netmiko import ConnectHandler, redispatch


def operating_system(ssh_session):
    """
    Accepts an active ssh connection
    Probes the ouuput of show version for what is contained in the output
    Will change the os on the ssh connection if a version is connected.
    Returns the os in a string for use in other functions
    """

    probe_output = ssh_session.send_command("show version")

    if "cisco" in probe_output:
        logging.info("OS fingerprint match: Cisco.  Redispatching...")
        redispatch(ssh_session, device_type="cisco_ios")
        return "cisco"

    elif "ExtremeXOS" in probe_output:
        logging.info("OS fingerprint match: EXOS.  Redispatching...")
        redispatch(ssh_session, device_type="extreme_exos")
        return "exos"
    elif "SLX" in probe_output:
        logging.info("OS fingerprint match: SLX-OS. Redispatching...")
        redispatch(ssh_session, device_type="extreme_slx")
        return "slx"
    elif "Invalid input" in probe_output:
        voss_probe = ssh_session.send_command("show sys-info")
        if "Invalid input" not in voss_probe:
            logging.info("OS fingerprint match: VOSS Redispatching...")
            redispatch(ssh_session, device_type="extreme_vsp")

    logging.error("OS detetcion failed no fingerprints matched")
    return None
