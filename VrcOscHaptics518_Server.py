from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
import websockets
import asyncio
import threading

# WebSocket server address (replace with your ESP8266 IP address)
server_address = "ws://HapticESP-1:8080"

# Number of boolean outputs
num_outputs = 6

# Initialize the boolean values and previous state
bool_values = [False] * num_outputs
prev_bool_values = bool_values.copy()

# OSC message handler
def handle_osc_message(address, *args):
    global bool_values
    if address.startswith("/avatar/parameters/L_Arm"):
        try:
            index = int(address.split("/")[-1][len("L_Arm") : ]) - 1
            if 0 <= index < num_outputs:
                if len(args) > 0 and isinstance(args[0], bool):
                    bool_values[index] = args[0]
                else:
                    print("Invalid argument:", args)
            else:
                print("Invalid index:", index + 1)
        except ValueError:
            print("Invalid address format:", address)

    #print("Received OSC message:", address, args)

# WebSocket client function
async def send_data():
    global prev_bool_values  # Declare prev_bool_values as global
    async with websockets.connect(server_address) as ws:
        while True:
            # Check if there is a difference between the current state and the previous state
            if bool_values != prev_bool_values:
                # Convert the boolean values to a string payload
                payload = "".join("1" if value else "0" for value in bool_values)

                # Send the payload to the ESP8266
                await ws.send(payload)

                # Print the payload sent
                print("Sent data:", payload)

                # Update the previous state
                prev_bool_values = bool_values.copy()

            # Delay for 100 milliseconds
            await asyncio.sleep(0.1)

# Start OSC server and run the WebSocket client
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

    # Run the WebSocket client
    try:
        loop.run_until_complete(send_data())
    except Exception as e:
        print("WebSocket client error:", str(e))
    finally:
        # Clean up resources
        server.shutdown()
        server_thread.join()
        print("OSC server stopped.")







'''
import time
import random
import websockets
import asyncio

# Number of boolean outputs
num_outputs = 8

# WebSocket server address (replace with your ESP8266 IP address)
server_address = "ws://192.168.0.75:8080"

async def send_data():
    async with websockets.connect(server_address) as ws:
        while True:
            # Send data for 5 seconds
            start_time = time.time()
            while time.time() - start_time < 5:
                # Generate a random index from 0 to num_outputs-1
                index = random.randint(0, num_outputs - 1)

                # Create a list of boolean values
                data = ['0'] * num_outputs
                data[index] = '1'

                # Convert the list to a string
                payload = ''.join(data)

                # Send the payload to the ESP8266
                await ws.send(payload)

                # Print the payload sent
                print("Sent data:", payload)

                # Delay for 100 milliseconds
                await asyncio.sleep(0.1)

            # Stop for 5 seconds
            await asyncio.sleep(5)

# Run the WebSocket client
asyncio.get_event_loop().run_until_complete(send_data())

'''

#const char* ssid = "VR-Gehirnwaescheeinheit24";
#const char* password = "LidBd21J";
#const char* server_ip = "192.168.0.29";
# uri = "ws://192.168.0.90:8080"