import logging

from netmiko import log
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
        device_type_info = switchdict.get("device_type")
        if isinstance(device_type_info, dict):
            model = device_type_info.get("model")
            manufacturer_name = switchdict.pop("cf_manufacturer", "Generic")
            device_type = get_or_create_device_type(nb, model, manufacturer_name)
            if not device_type:
                logging.error(f"Skipping switch upload: device type '{model}' unresolved")
                return
            switchdict["device_type"] = {"id": device_type.id}
        # existing_switch = nb.dcim.devices.filter(switchdict["name"])
        search_results = nb.dcim.devices.filter(name=switchdict["name"])
        results_list = list(search_results)
        existing_switch = None

        if len(results_list) > 0:
            existing_switch = results_list[0]
            logging.debug(f"Potential existing switch: {existing_switch}")
        if existing_switch:
            logging.info("Switch already exists. Checking differences...")
            needs_update = False

            for key, local_value in switchdict.items():
                server_attr = getattr(existing_switch, key)
                if isinstance(local_value, dict):
                    local_compare =  next(iter(local_value.values()), None)
                    server_value = (
                        server_attr.name if hasattr(server_attr, "name") else server_attr
                    )
                else:
                    local_compare = local_value
                    server_value = (
                        server_attr.name if hasattr(server_attr, "name") else server_attr
                    )

                if str(server_value).lower() != str(local_compare).lower():
                    logging.debug(
                        f"Mismatch found in {key}: Local is '{local_compare}', Server is '{server_value}'"
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


def get_or_create_manufacturer(nb, name):
    manufacturer = nb.dcim.manufacturers.get(name=name)
    if manufacturer:
        return manufacturer

    logging.info(f"Manufacturer '{name}' not found in NetBox. Creating it...")
    slug = name.lower().replace(" ", "-")
    try:
        return nb.dcim.manufacturers.create(name=name, slug=slug)
    except pynetbox.RequestError as e:
        logging.error(f"Could not create manufacturer '{name}': {e}")
        return None


def get_or_create_device_type(nb, model, manufacturer_name="Generic"):
    logging.info(f"Checking if device type '{model}' exists in NetBox...")
    device_type = nb.dcim.device_types.get(model=model)
    if device_type:
        logging.info(f"Device type '{model}' found in NetBox.")
        return device_type

    logging.info(f"Device type '{model}' not found in NetBox. Creating it...")
    manufacturer = get_or_create_manufacturer(nb, manufacturer_name)
    if not manufacturer:
        logging.error(f"Cannot create device type '{model}' without a manufacturer")
        return None

    slug = model.lower().replace(" ", "-")
    try:
        return nb.dcim.device_types.create(
            model=model,
            slug=slug,
            manufacturer=manufacturer.id,
        )
    except pynetbox.RequestError as e:
        logging.error(f"Could not create device type '{model}': {e}")
        return None
