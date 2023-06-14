import random
import time
from pythonosc import udp_client

# OSC Client parameters
osc_server_ip = '127.0.0.1'  # Replace with the IP address of your OSC server
osc_server_port = 9001       # Replace with the port number of your OSC server

# Create OSC client
client = udp_client.SimpleUDPClient(osc_server_ip, osc_server_port)

while True:
    # Generate a random number from 1 to 16
    random_number = random.randint(1, 16)

    # Create the address with the random number
    address = '/avatar/parameters/Sensor{}'.format(random_number)

    # Send a random boolean as the parameter value
    random_bool = random.choice([True, False])
    print(f"Send {address} {random_bool}")
    client.send_message(address, random_bool)

    # Wait for 1 second
    time.sleep(0.01)
