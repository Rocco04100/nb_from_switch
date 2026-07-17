import logging
import pynetbox
import ipaddress


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
    device_type = nb.dcim.device_types.get(model=model)
    if device_type:
        return device_type

    logging.info(f"Device type '{model}' not found in NetBox. Creating it...")
    manufacturer = get_or_create_manufacturer(nb, manufacturer_name)
    if not manufacturer:
        return None

    slug = model.lower().replace(" ", "-")
    try:
        return nb.dcim.device_types.create(model=model, slug=slug, manufacturer=manufacturer.id)
    except pynetbox.RequestError as e:
        logging.error(f"Could not create device type '{model}': {e}")
        return None


def get_or_create_role(nb, name):
    role = nb.dcim.device_roles.get(name=name)
    if role:
        return role

    logging.info(f"Device role '{name}' not found in NetBox. Creating it...")
    slug = name.lower().replace(" ", "-")
    try:
        return nb.dcim.device_roles.create(name=name, slug=slug, color="9e9e9e")
    except pynetbox.RequestError as e:
        logging.error(f"Could not create device role '{name}': {e}")
        return None


def resolve_relations(nb, devicedict):
    """
    Resolves nested lookup dicts (device_type, role) into real NetBox IDs,
    creating the referenced object if it doesn't exist yet.
    Mutates and returns devicedict, or None if a required relation couldn't be resolved.
    """
    device_type_info = devicedict.get("device_type")
    if isinstance(device_type_info, dict):
        model = device_type_info.get("model")
        manufacturer_name = devicedict.pop("cf_manufacturer", "Generic")
        device_type = get_or_create_device_type(nb, model, manufacturer_name)
        if not device_type:
            return None
        devicedict["device_type"] = {"model": device_type.model}

    role_info = devicedict.get("role")
    if isinstance(role_info, dict):
        role = get_or_create_role(nb, role_info.get("name"))
        if not role:
            return None
        devicedict["role"] = {"name": role.name}

    return devicedict


def post_device(nb, devicedict):
    """
    Generic create-or-update for a single NetBox device dict.
    Used for both the local switch and each discovered connected device.
    """
    devicedict = resolve_relations(nb, devicedict)
    logging.debug(f"device dict: {devicedict}")


    if devicedict is None:
        logging.error("Skipping device upload: could not resolve required relations")
        return None

    devicedict = {k: v for k, v in devicedict.items() if not k.startswith("_")}

    logging.info(f"Uploading device '{devicedict.get('name')}' to nb")
    logging.debug(f"The dict we are uploading: {devicedict}")

    try:
        search_results = nb.dcim.devices.filter(name=devicedict["name"])
        results_list = list(search_results)
        existing_device = results_list[0] if results_list else None

        if existing_device:
            logging.info(f"'{devicedict['name']}' already exists. Checking differences...")
            needs_update = False
            for key, local_value in devicedict.items():
                server_attr = getattr(existing_device, key, None)

                local_name = get_relation_name(local_value)
                server_name = get_relation_name(server_attr)
                if str(server_name).casefold() == str(local_name).casefold():
                    continue
                logging.info(
                    f"Mismatch found in {key}: "
                    f"Local is '{local_name}', Server is '{server_name}'"
                )
                setattr(existing_device, key, local_value)
                needs_update = True

            if needs_update:
                existing_device.save()
                logging.info("Updated succesfully!")
            else:
                logging.info("Everything matches! No update needed")
            return existing_device

        device = nb.dcim.devices.create(devicedict)
        logging.info(f"'{devicedict['name']}' succesfully uploaded to nb!")
        logging.debug(f"Uploaded device -> id: {device.id}, url: {device.url}")
        return device

    except pynetbox.RequestError as e:
        logging.error(f"Could not post device: {e}")
    except Exception as e:
        logging.error(f"Could not post device: {e}")
    return None


def post_switch(nb, switchdict):
    ports_list = switchdict.pop("_ports")
    switch_posted = post_device(nb, switchdict)
    for port in ports_list[1:]:
        get_or_create_interface(nb, switch_posted, port["port"], port["type"])
    return switch_posted


def post_connected_devices(nb, devices, switch_device):
    """
    Loops over the list of device dicts from parse.connected_devices()
    and creates/updates each one in NetBox.
    """
    results = []
    for device in devices:
        devicedict = dict(device)
        local_iface_name = devicedict.pop("_local_interface", None)
        remote_iface_name = devicedict.pop("_remote_interface", "NIC")
        discovered_ip = devicedict.pop("_ip_address", None)

        nb_device = post_device(nb, devicedict)
        results.append(nb_device)
        if not nb_device:
            continue

        switch_iface = get_or_create_interface(nb, switch_device, local_iface_name)
        device_iface = get_or_create_interface(nb, nb_device, remote_iface_name)
        get_or_create_cable(nb, switch_iface, device_iface)

        ip_record = get_or_create_ip_address(nb, discovered_ip, device_iface)
        if ip_record:
            set_primary_ip(nb_device, ip_record)

    succeeded = sum(1 for r in results if r)
    logging.info(f"Connected devices upload complete: {succeeded}/{len(devices)} succeeded")
    return results


def get_or_create_interface(nb, device, name, iface_type="other"):
    logging.info(f"Checking if we need to create, {name} on {device}...")
    if not device or not name:
        return None

    interface = nb.dcim.interfaces.get(device_id=device.id, name=name)
    if interface:
        logging.info("Interface found! No need to create")
        return interface

    logging.info(f"Interface '{name}' not found on '{device.name}'. Creating it...")
    try:
        return nb.dcim.interfaces.create(device=device.id, name=name, type=iface_type)
    except pynetbox.RequestError as e:
        logging.error(f"Could not create interface '{name}' on '{device.name}': {e}")
        return None


def get_or_create_cable(nb, interface_a, interface_b):
    if not interface_a or not interface_b:
        return None

    if getattr(interface_a, "cable", None) or getattr(interface_b, "cable", None):
        logging.debug(
            f"'{interface_a.device.name}:{interface_a.name}' or "
            f"'{interface_b.device.name}:{interface_b.name}' already cabled, skipping"
        )
        return None

    logging.info(
        f"Creating cable: {interface_a.device.name}:{interface_a.name} <-> "
        f"{interface_b.device.name}:{interface_b.name}"
    )
    try:
        return nb.dcim.cables.create(
            a_terminations=[{"object_type": "dcim.interface", "object_id": interface_a.id}],
            b_terminations=[{"object_type": "dcim.interface", "object_id": interface_b.id}],
        )
    except pynetbox.RequestError as e:
        logging.error(f"Could not create cable: {e}")
        return None


def get_or_create_ip_address(nb, address, interface):

    if not address:
        logging.warning("Connected device has no discovered IP address; skipping IP upload")
        return None

    if not interface:
        logging.warning(
            f"Could not assign discovered IP '{address}': device interface is missing"
        )
        return None

    try:
        raw_address = str(address).strip()

        # NetBox requires IP addresses in CIDR notation.
        if "/" not in raw_address:
            parsed = ipaddress.ip_address(raw_address)
            prefix_length = 32 if parsed.version == 4 else 128
            raw_address = f"{raw_address}/{prefix_length}"

        normalized_address = str(ipaddress.ip_interface(raw_address))
    except ValueError:
        logging.error(f"Invalid IP address discovered: '{address}'")
        return None

    try:
        matches = list(nb.ipam.ip_addresses.filter(address=normalized_address))
        existing_ip = matches[0] if matches else None

        if existing_ip:
            assigned_object = getattr(existing_ip, "assigned_object", None)

            if assigned_object and assigned_object.id != interface.id:
                logging.warning(
                    f"IP '{normalized_address}' is already assigned to another "
                    "NetBox object; not moving it"
                )
                return None

            if not assigned_object:
                existing_ip.assigned_object_type = "dcim.interface"
                existing_ip.assigned_object_id = interface.id
                existing_ip.save()
                logging.info(
                    f"Assigned existing IP '{normalized_address}' to "
                    f"'{interface.device.name}:{interface.name}'"
                )

            return existing_ip

        ip_record = nb.ipam.ip_addresses.create(
            address=normalized_address,
            status="active",
            assigned_object_type="dcim.interface",
            assigned_object_id=interface.id,
        )
        logging.info(
            f"Created IP '{normalized_address}' on "
            f"'{interface.device.name}:{interface.name}'"
        )
        return ip_record

    except pynetbox.RequestError as e:
        logging.error(f"Could not create or assign IP '{normalized_address}': {e}")
        return None


def set_primary_ip(device, ip_record):
    logging.debug(f"setting {ip_record} as primary IP for {device.name}")
    if not device or not ip_record:
        return False

    try:
        version = ipaddress.ip_interface(str(ip_record.address)).version
        primary_field = "primary_ip4" if version == 4 else "primary_ip6"

        current_primary = getattr(device, primary_field, None)
        if getattr(current_primary, "id", None) == ip_record.id:
            return True

        setattr(device, primary_field, ip_record.id)
        device.save()

        logging.info(
            f"Set '{ip_record.address}' as {primary_field} for '{device.name}'"
        )
        return True

    except (ValueError, pynetbox.RequestError) as e:
        logging.error(f"Could not set primary IP for '{device.name}': {e}")
        return False


def get_relation_name(value):
    if value is None:
           return None

    fields = ("name", "model", "value", "label", "id")

    if isinstance(value, dict):
        for field in fields:
            field_value = value.get(field)
            if field_value is not None:
                return field_value
        return str(value)

    for field in fields:
        field_value = getattr(value, field, None)
        if field_value is not None:
            return field_value

    return value
