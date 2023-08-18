from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
import websockets
import asyncio
import threading
import time

# WebSocket server addresses (replace with your ESP8266 IP addresses)
server_addresses = [
    "ws://ESP-L-Arm:8080",
    "ws://ESP-F-Body:8080",
    "ws://ESP-R-Body:8080",
    "ws://ESP-R-Arm:8080",
    "ws://ESP-Head:8080",
    "ws://ESP-L-Leg:8080",
    "ws://ESP-R-Leg:8080",
    "ws://ESP-Extra:8080",
]

# Number of boolean outputs
num_outputs = 128

# Configuration for each ESP: start and stop numbers
esp_config = [
    {"name": "ESP-L-Arm", "start": 1, "stop": 16, "in_use": True},
    {"name": "ESP-F-Body", "start": 17, "stop": 32, "in_use": True},
    {"name": "ESP-R-Body", "start": 33, "stop": 48, "in_use": False},
    {"name": "ESP-R-Arm", "start": 49, "stop": 64, "in_use": False},
    {"name": "ESP-Head", "start": 65, "stop": 80, "in_use": False},
    {"name": "ESP-L-Leg", "start": 81, "stop": 96, "in_use": False},
    {"name": "ESP-R-Leg", "start": 97, "stop": 112, "in_use": False},
    {"name": "ESP-Extra", "start": 113, "stop": 128, "in_use": False}
]

# Initialize the boolean values and previous state
bool_values = [False] * num_outputs
prev_bool_values = bool_values.copy()

# OSC message handler
def handle_osc_message(address, *args):
    global bool_values
    if address.startswith("/avatar/parameters/Sensor"):
        try:
            index = int(address.split("/")[-1][len("Sensor"):]) - 1
            if 0 <= index < num_outputs:
                if len(args) > 0 and isinstance(args[0], bool):
                    bool_values[index] = args[0]
                else:
                    print("Invalid argument:", args)
            else:
                print("Invalid index:", index + 1)
        except ValueError:
            print("Invalid address format:", address)

    # print("Received OSC message:", address, args)  #uncomment if you want to see all OSC messages


# WebSocket client function
async def send_data(server_address, start_index, end_index, in_use):
    global prev_bool_values  # Declare prev_bool_values as global
    while in_use:
        try:
            async with websockets.connect(server_address) as ws:
                print("Connected to", server_address)
                while in_use:
                    # Check if there is a difference between the current state and the previous state
                    if bool_values[start_index:end_index] != prev_bool_values[start_index:end_index]:
                        # Convert the boolean values to a string payload
                        payload = "".join(
                            "1" if value else "0" for value in bool_values[start_index:end_index]
                        )

                        # Send the payload to the ESP8266
                        await ws.send(payload)

                        # Print the payload sent
                        print("Sent data to", server_address, ":", payload)

                        # Update the previous state
                        prev_bool_values[start_index:end_index] = bool_values[start_index:end_index]

                    # Delay 0.1 for max cpu effitiency 0.01 for max speed
                    await asyncio.sleep(0.03)
        except Exception as e:
            print("WebSocket client error:", str(e))
            print("Failed to connect to", server_address)

        # Wait for 1 second before reconnecting
        await asyncio.sleep(1)


# Start OSC server and run the WebSocket clients
if __name__ == "__main__":
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(handle_osc_message)

    # Create the OSC server on localhost and port 9001
    server = BlockingOSCUDPServer(("localhost", 9001), dispatcher)
    print("OSC server listening on {}".format(server.server_address))

    # Start the OSC server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    print("OSC server started.")

    # Create and set up a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run the WebSocket clients for available ESPs
    tasks = []
    for i, server_address in enumerate(server_addresses):
        if i < len(esp_config) and esp_config[i]["in_use"]:
            start_index = esp_config[i]["start"] - 1
            end_index = esp_config[i]["stop"]
            task = asyncio.ensure_future(send_data(server_address, start_index, end_index, esp_config[i]["in_use"]))
            tasks.append(task)
        elif i < len(esp_config):
            print("ESP configuration missing for server address:", server_address)
        else:
            print("Invalid server address:", server_address)

    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up resources
        server.shutdown()
        server_thread.join()
        print("OSC server stopped.")