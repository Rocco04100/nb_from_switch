#!/home/noc/Desktop/nb_from_switch/.venv/bin/python3
import argparse
import logging
import os

import pynetbox
from dotenv import load_dotenv
from netmiko import ConnectHandler

from collector import get_device_data, get_switch_data
import nbapi
import parse

load_dotenv()
netbox_url = os.getenv("NETBOX_URL")
netbox_token = os.getenv("NETBOX_TOKEN")
if not netbox_url or not netbox_token:
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


###########################################
# command and switch setup later edit to loop through ip's
######################################
commands = [
    # "show version",
    # "show interfaces",
    # "show ip interface brief",
    # "show interface status",
    "show ip arp",  # Maps IP -> MAC
    "show mac address-table dynamic",  # Maps MAC -> Port
    "show lldp neighbors detail",  # Identifies Network Devices
]
switch = {
    "device_type": "generic",
    "host": "192.168.1.2",
    "username": "admin",
    "password": "password1",
    # "secret": "",
    "conn_timeout": 15,
    "auth_timeout": 15,
    "global_delay_factor": 2,
}

"""
SWITCH CONNECTION -> GATHER AND CLEAN UP
"""
try:
    logging.info(f"Connecting to {switch['host']}...")
    net_connect = ConnectHandler(**switch)

    switch_info = get_switch_data(net_connect)
    logging.critical(f"{switch_info}")
    device_data = get_device_data(net_connect, commands)

    connected_devices = parse.connected_devices(device_data)
    local_switch = parse.local_switch(net_connect, switch_info, switch["host"])
    if net_connect:
        net_connect.disconnect()
        logging.info("Connection closed.")

    """
    NETBOX CONNECTION -> CALL nbapi FUNCTIONS
    """

    logging.info("Connecting to nb api via pynetbox...")
    nb = pynetbox.api(
        netbox_url,
        token=netbox_token,
    )
    switch_device = None
    if local_switch:
        switch_device = nbapi.post_switch(nb, local_switch)
    if connected_devices:
        nbapi.post_connected_devices(nb, connected_devices, switch_device)
#
#
#
# test spot
#
# device_info = {
#         "name": "BOB TEST SWITCH",
#         "site": {"name": "D. S. Weaver Labs"},
#         "device_type": {"model": "some cisco"},
#         "role": {"name": "Access Switch"},
#         "status": "active",

#     }
#     nbapi.post_switch(nb, device_info)
except Exception as e:
    logging.error(f"Unhandled error:{e}")
