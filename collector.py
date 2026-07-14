import json

from netmiko import ConnectHandler


def get_data(switch, commands: list):
    """
    ###############################################################
    - Outputs a dictionary of raw data from a command using TextFSM
    - Needs the switch to run it on and the commands we will be running
    - Data is not clean for netbox so need to use parse in main
    - Will abort if the operating system is not properly detected
    ###############################################################
    """
    print(f"Connecting to {switch['host']}...")
    outputs_dict = {}
    net_connect = None
    if switch["device_type"] is None:
        print("Operating Sytem not detected aborting...")
        return

    net_connect = ConnectHandler(**switch)

    if isinstance(
        commands, str
    ):  # convert single string command to list so for loop can work with single commands too
        commands = [commands]

    for command in commands:
        try:
            output = net_connect.send_command(
                command, read_timeout=30, use_textfsm=True
            )
            if isinstance(output, list):
                print(f"--- {command} (Parsed) ---")
                outputs_dict[command] = output
            else:
                print(f"--- {command} (Raw) ---")
                # if text is not parsed it still adds raw output but flags it with COMMAND NOT PARSED
                outputs_dict[command] = {
                    "COMMAND NOT PARSED": command,
                    "raw_output": output,
                }

                print(
                    f"Error:'{command}' not parsed added to output as COMMAND NOT PARSED"
                )
                print(f"Ouput from command:{outputs_dict[command].get('raw_output')}")

        except Exception as e:
            print(f"Error: command output was unexpected(check syntax): {e}")

    if net_connect:
        net_connect.disconnect()
        print("\nConnection closed.")
    if outputs_dict:
        with open("output/raw_output.json", "w") as f:
            json.dump(output, f, indent=4)
        print(
            "\nRaw data collecting succesful! Raw output data is saved to raw_output.json"
        )
    else:
        print("Error: No raw output generated check commands")
    return outputs_dict
