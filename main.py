#!/home/noc/Desktop/nb_from_switch/.venv/bin/python3
import logging

import pynetbox
from netmiko import ConnectHandler

import nbapi
import parse
import startup
from collector import get_device_data, get_switch_data

configs = startup.initialize()
logging.debug("configs")
args = configs.get("args", "")
os_templates = configs.get("os_templates", "")
switch_list = configs.get("switch_list", "")
netbox_url = configs.get("creds", "").get("netbox_url", "")
netbox_token = configs.get("creds", "").get("netbox_token", "")


logging.debug(f"ARGS DETECTED: {args}")
logging.info("Loop start")

for switch in switch_list:
    logging.debug(f"The switch: {switch}")
    ip_address = switch["ip_address"]
    switch_user = switch.get("user")
    switch_password = switch.get("pass")
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
        logging.info(f"Connecting to {connection_params['host']}...")
        net_connect = ConnectHandler(**connection_params)

        switch_data = {}
        switch_data = get_switch_data(net_connect, os_templates)
        device_data = get_device_data(
            net_connect, os_templates, switch_data.get("OS"), ip_address
        )

        local_switch = parse.local_switch(
            net_connect, switch_data, connection_params["host"], args.test
        )
        connected_devices = parse.connected_devices(device_data, ip_address, args.test)

        if net_connect:
            net_connect.disconnect()
            logging.info("SSH connection closed.")

        """
        NETBOX CONNECTION -> CALL nbapi FUNCTIONS
        """
        if args.dry:
            logging.info(
                "Dry run detected - data not uploaded to netbox check outputs for results"
            )
        else:
            logging.info("Connecting to nb api via pynetbox...")
            nb = pynetbox.api(
                netbox_url,
                token=netbox_token,
            )
            switch_device = None
            if local_switch:
                switch_device = nbapi.post_switch(nb, local_switch)
                nbapi.post_connected_devices(nb, connected_devices, switch_device)
    except Exception as e:
        logging.error(f"Unhandled error:{e}")
logging.info("Loop end")
