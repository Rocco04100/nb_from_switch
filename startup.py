import logging
import argparse
import json
from dotenv import load_dotenv
import os
import csv

def initialize():
    args = setup_args()
    setup_log(args.log)

    logging.info("Initiallizing...")

    return{
    "os_templates": validate_os_templates(),
    "creds": validate_creds(),
    "args": args,
    "switch_list": validate_switch_list(),
    }


def validate_os_templates():
    REQUIRED_KEYS = {
        "version_command",
        "device_type",
        "ports_command",
        "arp_command",
        "mac_command",
        "lldp_command",
        "textfsm_templates",
    }

    REQUIRED_TEMPLATES = {
        "version",
        "ports",
        "arp",
        "mac",
        "lldp",
    }
    os_templates = {}
    try:
        with open("config/os_templates.json") as f:
            os_templates = json.load(f)

        if not isinstance(os_templates, dict):
            raise ValueError("os_templates.json must contain a JSON object.")

        for os_name, config in os_templates.items():
            if not isinstance(config, dict):
                raise ValueError(f"{os_name} must be a JSON object.")

            missing = REQUIRED_KEYS - config.keys()
            if missing:
                raise ValueError(
                    f"{os_name} is missing required keys: {', '.join(sorted(missing))}"
                )

            if not isinstance(config["textfsm_templates"], dict):
                raise ValueError(
                    f"{os_name}.textfsm_templates must be a JSON object."
                )

            missing_templates = (
                REQUIRED_TEMPLATES - config["textfsm_templates"].keys()
            )
            if missing_templates:
                raise ValueError(
                    f"{os_name}.textfsm_templates is missing: "
                    f"{', '.join(sorted(missing_templates))}"
                )
        logging.info("OS templates validated successfully.")
        return os_templates
    except Exception as e:
        logging.critical(f"Invalid os_templates.json: {e}")
        raise


def validate_creds():
    load_dotenv()
    netbox_url = os.getenv("NETBOX_URL")
    netbox_token = os.getenv("NETBOX_TOKEN")

    if not netbox_url or not netbox_token:
        raise ValueError("Missing netbox credentials! check you .env file")
    return {
        "netbox_url": netbox_url,
        "netbox_token": netbox_token,
    }


def validate_switch_list():
    try:
        with open("config/switches.csv", mode="r") as f:
            reader = csv.DictReader(f)
            switch_list = list(reader)
        logging.debug(f"Switch ip's found: {switch_list}")
    except Exception as e:
        logging.critical("Switch ip's not found in config folder aborting...")
        raise Exception(e)
    return switch_list


def setup_args():
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
    return args


def setup_log(level):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(module)s %(levelname)s - %(message)s",
        force=True
    )
    logging.getLogger("netmiko").setLevel(logging.WARN)
    logging.getLogger("paramiko").setLevel(logging.WARN)
    logging.getLogger("pynetbox").setLevel(logging.WARN)
