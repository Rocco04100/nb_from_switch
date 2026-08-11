#!/home/noc/Desktop/nb_from_switch/.venv/bin/python3
import logging

import pynetbox
from netmiko import ConnectHandler

import nbapi
import parse
import startup
from collector import get_device_data, get_switch_data

logger = logging.getLogger(__name__)

configs = startup.initialize()
logger.debug(f"configs loaded")
args = configs.get("args", "")
os_templates = configs.get("os_templates", "")
switch_list = configs.get("switch_list", "")
netbox_url = configs.get("creds", "").get("netbox_url", "")
netbox_token = configs.get("creds", "").get("netbox_token", "")
switch_user = configs.get("creds", "").get("switch_user", "")
switch_password = configs.get("creds", "").get("switch_password", "")


logger.debug(f"ARGS DETECTED: {args}")

# set up netbox connection outside of loop so we only need one for all switches
if args.dry:
    logger.info(
        "Dry run detected - data will not be uploaded to netbox check outputs/ for results"
    )
    nb = None
else:
    logger.info("Connecting to nb api via pynetbox...")
    nb = pynetbox.api(
        netbox_url,
        token=netbox_token,
    )

logger.info("-----------------------MAIN LOOP START-----------------------")
for switch in switch_list:
    logger.debug(f"The switch: {switch}")
    ip_address = switch["ip_address"]
    connection_params = {
        "device_type": "generic",
        "host": ip_address,
        "username": switch_user,
        "password": switch_password,
        # "secret": "",
        "conn_timeout": 15,
        "auth_timeout": 15,
        "global_delay_factor": 2,
    }
    try:
        """
        SWITCH CONNECTION -> GATHER AND CLEAN UP
        """
        logger.info(f"Connecting to {connection_params['host']}...")
        net_connect = ConnectHandler(**connection_params)

        switch_data = {}
        switch_data = get_switch_data(net_connect, os_templates)
        os_template = os_templates.get(switch_data.get("OS"))

        device_data = get_device_data(
            net_connect, os_templates, switch_data.get("OS"), ip_address
        )

        local_switch = parse.local_switch(
            net_connect, switch_data, connection_params["host"], os_template, args.test
        )
        connected_devices = parse.connected_devices(device_data, ip_address, args.test)

        if net_connect:
            net_connect.disconnect()
            logger.info("SSH connection closed.")

        """
        NETBOX CONNECTION -> CALL nbapi FUNCTIONS
        """
        switch_device = None
        if local_switch and nb:
            switch_device = nbapi.post_switch(nb, local_switch)
            if args.connected:
                logger.warning("ATTEMPTING EXPEREMENTAL CONNECTED DEVICE UPLOAD")
                nbapi.post_connected_devices(nb, connected_devices, switch_device)
    except Exception as e:
        logger.error(f"Unhandled error:{e}")
logger.info("-----------------------MAIN LOOP END-----------------------")
