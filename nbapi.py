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
        # existing_switch = nb.dcim.devices.filter(switchdict["name"])
        search_results = nb.dcim.devices.filter(name=switchdict["name"])
        results_list = list(search_results)
        if len(results_list) > 0:
            existing_switch = results_list[0]
            logging.debug(f"Potential existing switch: {existing_switch}")
        if existing_switch:
            logging.info("Switch already exists. Checking differences...")
            needs_update = False

            for key, local_value in switchdict.items():
                server_attr = getattr(existing_switch, key)
                server_value = (
                    server_attr.id if hasattr(server_attr, "id") else server_attr
                )

                if str(server_value).lower() != str(local_value).lower():
                    logging.debug(
                        f"Mismatch found in {key}: Local is '{local_value}', Server is '{server_value}'"
                    )
                    setattr(existing_switch, key, local_value)
                    needs_update = True
            if needs_update:
                logging.info("Mistmatched Updating...")
                existing_switch.save()
                logging.info("Updated succesfully!")
            else:
                logging.info("Everything matches! No update needed")
        else:
            switch = nb.dcim.devices.create(switchdict)

            logging.info("Switch succesfully uploaded to nb!")
            logging.debug(f"Type of object uploaded: {type(switch)}")
            logging.debug(f"Switches url: {switch.url}")
            logging.debug(f"Switches id: {switch.id}")
    except pynetbox.RequestError as e:
        logging.error(f"POST: {e}")
    except Exception as e:
        logging.debug(f"Posting switch: {e}")
