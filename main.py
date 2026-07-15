import argparse
import logging

import pynetbox
from netmiko import ConnectHandler

import collector
import detect
import nbapi
import parse

###########################################
# argparse setup
######################################
parser = argparse.ArgumentParser(
    description="Loops through given IP's and gathers data for netbox"
)
parser.add_argument(
    "-l",
    "--log",
    default="WARNING",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    type=str.upper,
    help="Set the level of logs you see the higher the level the less logs you see(debug shows all)",
)
args = parser.parse_args()
###########################################
# Logging setup
######################################
logging.basicConfig(
    level=getattr(logging, args.log()),
    format="%(asctime)s %(levelname)s - %(message)s",
)
logging.getLogger("netmiko").setLevel(logging.WARN)
logging.getLogger("paramiko").setLevel(logging.WARN)

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

# site_ids = nbapi.get_sites_id(nb)
#
#  net_connect = None
#
# ############################
# Calling the functions
# #############################
"""
SWITCH CONNECTION -> GATHER AND CLEAN UP
"""
# try:
#     logging.info(f"Connecting to {switch['host']}...")
#     net_connect = ConnectHandler(**switch)
#     detected_os = detect.operating_system(net_connect)
#     if detected_os:
#         switch["device_type"] = detected_os

#     output = collector.get_data(net_connect, commands)
#     connected_devices = parse.connected_devices(output)
#     local_switch = collector.get_switch(net_connect)
#     if net_connect:
#         net_connect.disconnect()
#         logging.info("Connection closed.")
# except Exception as e:
#     logging.error(e)


"""
NETBOX CONNECTION -> CALL nbapi FUNCTIONS
"""

try:
    # logging.info("Connecting to nb api via pynetbox...")
    # nb = pynetbox.api(
    #     "https://demo.netbox.dev/",
    #     token="5MR7eDSdwZirNB4B39EMdZbtqusxJENUdG7gqfLt",
    # )
    # # if local_switch:
    #     nbapi.post_switch(nb, local_switch)
    """
    Testing below
    """
    # thing = {
    #     "name": "BOBSWITCH",
    #     "status": "active",
    #     "site": 22,
    #     "device_type": 24,
    #     "role": 15,
    # }
    # device = nb.dcim.devices.create(thing)
    # logging.debug(f"Obeject device type: {type(device)}")
    # logging.debug(f"Live api url: {device.url}")
    # logging.debug(f"Assigned server id: {device.id}")


except Exception as e:
    logging.error(e)


# Token: 5MR7eDSdwZirNB4B39EMdZbtqusxJENUdG7gqfLt
# Bearer nbt_G9CYqjNOiL0f.8JrWDvvpQ9c6xp4yR9fQexQAqojU0yZUsUBvUdR5
