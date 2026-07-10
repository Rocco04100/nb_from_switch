# Serial port /dev/ttyUSB0
import serial
from netmiko import ConnectHandler

cisco_switch = {
    "device_type": "cisco_ios_serial",
    "username": "admin",
    "password": "",
    "secret": "",
    "fast_cli": False,  # Critical: Disable fast CLI for serial
    "conn_timeout": 30,  # Optional: Increase timeout for slow serial login
    "serial_settings": {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "bytesize": serial.EIGHTBITS,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
    },
}

print("Connecting to console port...")

try:
    net_connect = ConnectHandler(**cisco_switch)

    v_output = net_connect.send_command("show version", read_timeout=30)

    print("\n--- Show Version Output ---\n")
    print(v_output)

    m_output = net_connect.send_command("show mac address-table", read_timeout=30)
    print("\n--- Show mac Output ---\n")
    print(m_output)

    net_connect.disconnect()
    print("\nConnection closed.")

except Exception as e:
    print(f"\nConnection failed: {e}")

print("hello")
