# What it does

- It will loop through ip's in switches.csv and establish a ssh connection(currently hardcoded user and pass for test environment)
- It will run show version and search the raw string returned for the operating systems found in config/os_templates.json
- os_templates has commands and text fsm templates that make it so it can be run in multi vendor environment
- it will gather arp table, mac address table, and lldp neighbors detail info
- using this info it creates dictionaries the format netbox wants for device, interface, and ip upload before uploading it to netbox


# How to run on your device

1. dowload the python packages used by running pip install -r requirements.txt in your python environment
2. create output folder(used to show outputs when not uploading to netbox)
3. create your os templates, examples are in the repo they must have the same format
4. make textfsm files in a custom_template 
  - just throw the output of your command like show arp into ai and have it give you a textfsm template that returns the values you need
5. make sure you got the proper cred's(I havent done this part yet)
