import random
import time
from pythonosc import udp_client

# OSC Client parameters
osc_server_ip = '127.0.0.1'  # Replace with the IP address of your OSC server
osc_server_port = 9001       # Replace with the port number of your OSC server
mode = "setting"                # sensor, setting

# Create OSC client
client = udp_client.SimpleUDPClient(osc_server_ip, osc_server_port)

while True:
    if mode == "sensor":
        # Generate a random number from 1 to 16
        random_number = random.randint(1, 16)
        # Generate a random bool
        random_bool = random.choice([True, False])

        # Create the address with the random number
        address = '/avatar/parameters/Sensor{}'.format(random_number)

        # Send a random boolean as the parameter value
        print(f"Send {address} {random_bool}")
        client.send_message(address, random_bool)

    elif mode == "setting":
        # Generate a random float from 0.0 to 1.0
        random_float = random.randint(0, 100) / 100

        addresses = ['/avatar/parameters/SettingStrength',
                     '/avatar/parameters/SettingAttenuationTime']

        addressIndex = random.randint(0, len(addresses)-1)

        print(
            f"Send {addresses[addressIndex]} {random_float} ({int(random_float * 255)})")
        client.send_message(addresses[addressIndex], random_float)

    # Wait for random amount
    sleepTime = random.randint(1, 1) / 100
    time.sleep(sleepTime)
