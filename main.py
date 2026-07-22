#!/home/noc/Desktop/nb_from_switch/.venv/bin/python3
import argparse
import logging
import os
import json
import csv

import pynetbox
from dotenv import load_dotenv
from netmiko import ConnectHandler

from collector import get_device_data, get_switch_data
import nbapi
import parse

load_dotenv()
netbox_url = os.getenv("NETBOX_URL")
netbox_token = os.getenv("NETBOX_TOKEN")
switch_user = os.getenv("SWITCH_USER")
switch_password = os.getenv("SWITCH_PASSWORD")

if not netbox_url or not netbox_token or not switch_user:
    raise ValueError("Missing netbox credentials! check you .env file")
###########################################
# argparse setup
######################################
parser = argparse.ArgumentParser(
    description="Loops through given IP's and gathers data for netbox"
)
parser.add_argument(
    "-l",
    "--log",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    type=str.upper,
    help="Set the level of logs you see the higher the level the less logs you see(debug shows all)",
)
parser.add_argument(
    "-d",
    "--dry",
    action="store_true",
    help="Will not post to netbox check output file json's for what would be posted",
)
args = parser.parse_args()
###########################################
# Logging setup
######################################
logging.basicConfig(
    level=getattr(logging, args.log),
    format="%(asctime)s %(module)s %(levelname)s - %(message)s",
)
logging.getLogger("netmiko").setLevel(logging.WARN)
logging.getLogger("paramiko").setLevel(logging.WARN)
logging.getLogger("pynetbox").setLevel(logging.WARN)

"""
SETUP CONFIGS NEEDED
"""
os_templates = {}
try:
    with open("config/os_templates.json", 'r') as f:
        os_templates = json.load(f)
    logging.info("OS templates found succesfully!")
except Exception as e:
    logging.critical(f"os_templates.json not found in config folder aborting ERROR: {e}")
    raise Exception("os_templates are needed to run script")

try:
    with open("config/switches.csv", mode="r") as f:
        reader = csv.DictReader(f)
        switch_list = list(reader)
    logging.debug(f"Switch ip's found: {switch_list}")
except Exception as e:
    logging.critical("Switch ip's not found in config folder aborting...")
    raise Exception(e)
"""
SWITCH CONNECTION -> GATHER AND CLEAN UP
"""
logging.debug(f"ARGS DETECTED: {args}")
logging.info("Loop start")
for switch in switch_list:
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
        logging.info(f"Connecting to {connection_params['host']}...")
        net_connect = ConnectHandler(**connection_params)

        switch_data ={}
        switch_data = get_switch_data(net_connect, os_templates)
        device_data = get_device_data(net_connect, os_templates, switch_data.get("OS"), ip_address)

        local_switch = parse.local_switch(net_connect, switch_data, connection_params["host"])
        connected_devices = parse.connected_devices(device_data, ip_address)

        if net_connect:
            net_connect.disconnect()
            logging.info("SSH connection closed.")

        """
        NETBOX CONNECTION -> CALL nbapi FUNCTIONS
        """
        if(args.dry):
            logging.info("Dry run detected - data not uploaded to netbox check outputs for results")
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
