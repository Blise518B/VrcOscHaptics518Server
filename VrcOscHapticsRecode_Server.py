import asyncio
import threading
import websockets
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from asyncio_throttle import Throttler

esp_config = [
    {"name": "ESP-L-Arm", "address": "ws://ESP-L-Arm:8080",
        "start": 1, "stop": 16, "in_use": True},
    {"name": "ESP-F-Body", "address": "ws://ESP-F-Body:8080",
        "start": 17, "stop": 32, "in_use": True},
    {"name": "ESP-R-Body", "address": "ws://ESP-R-Body:8080",
        "start": 33, "stop": 48, "in_use": False},
    {"name": "ESP-R-Arm", "address": "ws://ESP-R-Arm:8080",
        "start": 49, "stop": 64, "in_use": False},
    {"name": "ESP-Head", "address": "ws://ESP-Head:8080",
        "start": 65, "stop": 80, "in_use": False},
    {"name": "ESP-L-Leg", "address": "ws://ESP-L-Leg:8080",
        "start": 81, "stop": 96, "in_use": True},
    {"name": "ESP-R-Leg", "address": "ws://ESP-R-Leg:8080",
        "start": 97, "stop": 112, "in_use": False},
    {"name": "ESP-Extra", "address": "ws://ESP-Extra:8080",
        "start": 113, "stop": 128, "in_use": False}
]

max_index = 128

# Initialize the boolean values and previous state
bool_values = [False] * max_index
prev_bool_values = bool_values.copy()

# Define the WebSocket clients
websocket_clients = {}

# Define the throttler for each client
throttlers = {}

# Define the data queues for each client
data_queues = {}

# Resolve SensorId to name


def get_client_name_from_sensor(sensor_id):
    for config in esp_config:
        if config["in_use"]:
            if config["start"] <= sensor_id and sensor_id <= config["stop"]:
                return config["name"]
    return None

# Resolve name to start and end


def get_start_and_end_by_client_name(client_name):
    for config in esp_config:
        if config["name"] == client_name:
            return config["start"], config["stop"]
    return None, None

# OSC message handler


def handle_osc_message(address, *args):

    if address.startswith("/avatar/parameters/Sensor"):
        try:
            index = int(address.split("/")[-1][len("Sensor"):])
            if 1 <= index <= max_index:
                if len(args) > 0 and isinstance(args[0], bool):

                    # Extract the client name from the Sensor
                    client_name = get_client_name_from_sensor(index)

                    if client_name is not None:
                        start_index, end_index = get_start_and_end_by_client_name(
                            client_name)
                        # Check for data changes
                        if bool_values[start_index:end_index] != prev_bool_values[start_index:end_index]:

                            # Convert OSC address and arguments to a string
                            data = "".join(
                                "1" if value else "0" for value in bool_values[start_index:end_index]
                            )

                            prev_bool_values[start_index:end_index] = bool_values[start_index:end_index]

                            # Check if the client is in use and has a WebSocket connection
                            if client_name in websocket_clients:
                                queue = data_queues[client_name]

                                # Store the data in the queue
                                queue.append(data)

                                # Trigger sending data to the WebSocket client
                                asyncio.create_task(
                                    send_data_to_client(client_name))
                    else:
                        print("Invalid index:", index)
                else:
                    print("Invalid argument:", args)
            else:
                print("Invalid index:", index)
        except ValueError:
            print("Invalid address format:", address)


# Function to send data to the WebSocket client


async def send_data_to_client(client_name):
    websocket = websocket_clients[client_name]
    queue = data_queues[client_name]
    throttler = throttlers[client_name]

    # Check if there is new data in the queue
    if queue:
        # Wait for the throttler to allow the next data sending
        await throttler.throttle()

        data = queue[-1]  # Use the newest data from the queue

        # Clear the queue
        queue.clear()

        # Send the data to the WebSocket client
        await websocket.send(data)


# Start the WebSocket clients
async def start_websocket_clients():
    for config in esp_config:
        if config["in_use"]:
            client_name = config["name"]
            client_url = config["address"]
            print(f"Connecting to {client_url}...")
            try:
                websocket = await websockets.connect(client_url)
                print(f"Connected to {client_url}")
                websocket_clients[client_name] = websocket
                data_queues[client_name] = []
                # Limit to 20 messages per second
                throttlers[client_name] = Throttler(rate_limit=20)
            except Exception as e:
                print("WebSocket client error:", str(e))
                print("Failed to connect to", client_url)

# Start the OSC server
dispatcher = Dispatcher()
dispatcher.set_default_handler(handle_osc_message)

# Create the OSC server on localhost and port 9001
server = BlockingOSCUDPServer(("localhost", 9001), dispatcher)
print("OSC server listening on {}".format(server.server_address))

# Start the OSC server in a separate thread
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()
print("OSC server started.")

# Run the event loop


async def main():
    await start_websocket_clients()

asyncio.run(main())
