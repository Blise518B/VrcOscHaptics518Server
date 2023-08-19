import random
import time
import websockets
from pythonosc import dispatcher
from pythonosc import osc_server
import asyncio

esp_config = [
    {"name": "ESP-L-Arm", "address": "ws://ESP-L-Arm:8080",
        "start": 1, "stop": 16, "in_use": True},
    {"name": "ESP-F-Body", "address": "ws://ESP-F-Body:8080",
        "start": 17, "stop": 32, "in_use": False},
    {"name": "ESP-R-Body", "address": "ws://ESP-R-Body:8080",
        "start": 33, "stop": 48, "in_use": False},
    {"name": "ESP-R-Arm", "address": "ws://ESP-R-Arm:8080",
        "start": 49, "stop": 64, "in_use": False},
    {"name": "ESP-Head", "address": "ws://ESP-Head:8080",
        "start": 65, "stop": 80, "in_use": False},
    {"name": "ESP-L-Leg", "address": "ws://ESP-L-Leg:8080",
        "start": 81, "stop": 96, "in_use": False},
    {"name": "ESP-R-Leg", "address": "ws://ESP-R-Leg:8080",
        "start": 97, "stop": 112, "in_use": False},
    {"name": "ESP-Extra", "address": "ws://ESP-Extra:8080",
        "start": 113, "stop": 128, "in_use": False}
]

strength = 0.5

max_index = 128

# Initialize the boolean values and previous state
pwm_values = [0] * max_index
prev_pwm_values = pwm_values.copy()

# Define the WebSocket clients
websocket_clients = {}

# Define the last_sent for each client
last_sent = {}

wait_lock = {}

# Define the data queues for each client
send_datas = {}


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
            return config["start"] - 1, config["stop"]
    return None, None


# OSC message handler
def handle_osc_message(address, *args):

    if address.startswith("/avatar/parameters/Sensor"):

        try:
            index = int(address.split("/")[-1][len("Sensor"):])
            if 1 <= index <= max_index:

                if len(args) > 0 and isinstance(args[0], bool):
                    pwm_values[index] = int((float(args[0]) * 255 * strength))
                    # Extract the client name from the Sensor
                    client_name = get_client_name_from_sensor(index)

                    if client_name is not None:

                        start_index, end_index = get_start_and_end_by_client_name(
                            client_name)
                        # Check for data changes
                        if pwm_values[start_index:end_index] != prev_pwm_values[start_index:end_index]:
                            # uncomment if you want to see all OSC messages
                            # print("Received OSC message:", address, args)

                            # Convert OSC data into bytes
                            data = bytearray(
                                pwm_values[start_index:end_index])

                            prev_pwm_values[start_index:end_index] = pwm_values[start_index:end_index]

                            # Check if the client is in use and has a WebSocket connection
                            if client_name in websocket_clients:
                                # Store the data to send
                                send_datas[client_name] = data

                                # Check if
                                lock = wait_lock[client_name]
                                if (not lock):
                                    # Trigger sending data to the WebSocket client
                                    asyncio.create_task(
                                        send_data_to_client(client_name=client_name))
                            else:
                                print(f"{client_name} is not connected")
                    else:
                        print("Invalid index:", index)
                else:
                    print("Invalid argument:", args)
            else:
                print("Invalid index:", index)
        except ValueError:
            print("Invalid address format:", address)
    # print("Received OSC message:", address, args)  #uncomment if you want to see all OSC messages


# Function to send data to the WebSocket client
async def send_data_to_client(client_name):
    # Limit to 20 messages per second/every 50ms per client

    # Skip if locked
    if (wait_lock[client_name]):
        return

    # Lock other sends
    wait_lock[client_name] = True

    # Wait to ensure throttle
    wait_time = 0.05 + last_sent[client_name] - time.time()
    # print(f"Wait: {wait_time}")
    if (wait_time > 0):
        await asyncio.sleep(wait_time)

    client_websocket = websocket_clients[client_name]

    # Check if there is new data to send
    if send_datas[client_name]:
        # Use the newest data
        send_data = send_datas[client_name]

        # Clear send data
        send_datas[client_name] = None

        # Uncomment to see what data will be sent
        # print("Send " + client_name + ": " + send_data)

        # Send the data to the WebSocket client
        try:
            await client_websocket.send(send_data)
        except websockets.exceptions.ConnectionClosed:
            print(f"WebSocket connection closed for {client_name}")
            # Remove the disconnected client
            del websocket_clients[client_name]
        last_sent[client_name] = time.time()
    wait_lock[client_name] = False


# Start the WebSocket clients
async def start_websocket_clients():
    while True:  # Run indefinitely
        for config in esp_config:
            if config["in_use"]:
                client_name = config["name"]
                client_url = config["address"]
                if client_name in websocket_clients:
                    if (websocket_clients[client_name].closed):
                        del websocket_clients[client_name]
                    continue  # Skip connection process for existing client
                print(f"Connecting to {client_name}: {client_url}...")
                try:
                    websocket = await websockets.connect(client_url, ping_timeout=1)
                    print(f"Connected to {client_url}")
                    websocket_clients[client_name] = websocket
                    send_datas[client_name] = []
                    last_sent[client_name] = time.time()
                    wait_lock[client_name] = False
                except Exception as e:
                    print("WebSocket client error:", str(e))
                    print("Failed to connect to", client_url)
                    continue  # Continue to the next iteration
        await asyncio.sleep(3)  # Delay before attempting to reconnect


async def start_osc_server():
    # Create an OSC dispatcher and register the message handler
    osc_dispatcher = dispatcher.Dispatcher()
    osc_dispatcher.set_default_handler(handle_osc_message)

    # Create an OSC server with the current event loop
    loop = asyncio.get_event_loop()
    osc_server_instance = osc_server.AsyncIOOSCUDPServer(
        ("127.0.0.1", 9001), osc_dispatcher, loop=loop)

    # Start the OSC server
    print("Starting OSC server...")
    await osc_server_instance.create_serve_endpoint()


async def main():
    # Start the OSC server asynchronously
    osc_task = asyncio.create_task(start_osc_server())

    # Start websockets
    websockets_task = asyncio.create_task(start_websocket_clients())

    # Wait for both tasks to complete
    await asyncio.gather(osc_task, websockets_task)

# Create the event loop and run it forever
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
except KeyboardInterrupt:
    loop.close()
    exit(0)
