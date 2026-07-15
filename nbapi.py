import logging

import pynetbox


def get_sites_id(nb):
    sites_tabel = {}
    try:
        sites = nb.dcim.sites.all()
        for site in sites:
            sites_tabel[site.name] = site.id
    except Exception as e:
        print(f"error happened: {e}")

    return sites_tabel


def post_switch(nb, switchdict):
    logging.info("Uploading switch to nb")
    logging.debug(f"The dict we are uploading: {(switchdict)}")
    try:
        switch = nb.dcim.devices.create(switchdict)

        logging.info("Switch succesfully uploaded to nb!")
        logging.debug(f"Type of object uploaded: {type(switch)}")
        logging.debug(f"Switches url: {switch.url}")
        logging.debug(f"Switches id: {switch.id}")
    except pynetbox.RequestError as e:
        logging.error(f"POST: {e}")
    except Exception as e:
        logging.error(f"Posting switch: {e}")
