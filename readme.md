# INFO

This has been untested for some time and I have made changes. My internship has ended and I no longer have access to enterprise switches to mess around on so I am unable to fully stress test.

# What it does

- It will loop through ip's in switches.csv and establish a ssh connection(currently hardcoded user and pass for test environment)
- It will run show version and search the raw string returned for the operating systems found in config/os_templates.json
- os_templates has commands and text fsm templates that make it so it can be run in multi vendor/os environment
- it will gather arp table, mac address table, and lldp neighbors detail info
- using this info it creates dictionaries the format netbox wants for connected devices, interfaces, and ip's upload before uploading it to netbox

# IMPORTANT

Right now it is unable to consider multiple macs from one port like trunk ports so by default it will only focus on uploading the switch data and you can review the connected device data, and upload it manually via json if you choose. There is an option to try the not working connected device upload but it probably won't work. My internship has ended and I no longer have access to enterprise switches to mess around on

# How to run on your device

1. download the python packages used by running pip install -r requirements.txt in your python environment
2. create output folder(used to show outputs when not uploading to netbox)
3. create your config folder
4. create custom_templates folder in config that contains folders of text_fsm templates there are examples, but typically throwing the output of a command into AI and asking for a textfsm template with the correct values works perfectly
5. create os_templates.json in config view below for explanation

{

"cisco"(Operating system name): {

"version_command": "show version",(A Command that contains a model, -> if it has mac and serial in it too this can be recorded)

"device_type": "cisco_ios",(the device type for netmiko drivers look up what it is for your os)

"manufacturer": "Cisco",(OPTIONAL typically just does an oui lookup for manufacturer)

"ports_command": "show interfaces status", (this is a command that must contain port names(Ex: ge1:1) and type(Ex: 1000baseT) )

"arp_command": "show ip arp", (this command must contain arp table or just macs mapped to ips so we can populate arp info)

"mac_command": "show mac address-table", (this command must contain data to map mac's to ports for cable creation)

"lldp_command": "show lldp neighbors detail", (OPTIONAL but required for connected devices to work)

"textfsm_templates": { (These are the names of the textfsm files for each command)

"version": "cisco_version.textfsm",

"ports": "cisco_interface.textfsm",

"arp": "cisco_arp.textfsm",

"mac": "cisco_mac.textfsm",

"lldp": "cisco_lldp.textfsm"

}

}

4.  create your switches.csv in config a simple csv file with one header called "ip_address" and populated with the ips of switches to ssh into

5.  Create your own .env file with correct variables and values
    NETBOX_URL=https://demo.netbox.dev/
    NETBOX_TOKEN=some token
    SWITCH_USER=admin
    SWITCH_PASSWORD=password1
6.  Ensure your device is allowed to ssh into the switches
7.  When running the script from cli use -h to view available flags (helpful for test runs)
8.  Run the script with ./main.py and pray
