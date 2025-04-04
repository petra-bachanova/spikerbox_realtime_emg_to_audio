# backend.py
import socketio
import time
import math
import random
import sys

import app.main

# Create a Socket.IO client
sio = socketio.Client(logger=False, engineio_logger=False)

# Track connection status
connected = False
streaming_enabled = True
start_time = None

# Generate simulated data
def generate_data():
    global start_time
    current_time = time.time() - start_time
    
    # Create a wave pattern with some random noise
    base_value = math.sin(current_time * 2) * 5  # Sine wave
    noise = random.uniform(-0.5, 0.5)  # Random noise
    value = base_value + noise
    
    return {
        'time': round(current_time, 2),
        'value': round(value, 2)
    }

# Connect to the frontend
@sio.event
def connect():
    global connected, start_time
    print("Backend connected to frontend server!")
    connected = True
    # Reset the start time when we connect
    start_time = time.time()
    # Request the current streaming state
    sio.emit('request_streaming_state')

@sio.event
def disconnect():
    global connected
    print("Backend disconnected from frontend server")
    connected = False

@sio.event
def streaming_state(data):
    global streaming_enabled
    streaming_enabled = data.get('active', True)
    state_text = "enabled" if streaming_enabled else "disabled"
    print(f"Streaming is now {state_text}")

def send_data():
    global connected, streaming_enabled
    
    while connected:
        # Only send data if streaming is enabled
        if streaming_enabled:
            """
            # Generate new data point
            data_point = generate_data()
            print(data_point)
            # Send to the frontend
            try:
                sio.emit('data_update', data_point)
            except Exception as e:
                print(f"Error sending data: {e}")
            """

        
        # Wait before sending next update (100ms = 0.1 seconds)
        time.sleep(0.1)

def connect_with_retry(url, max_retries=5, retry_delay=2):
    """Attempt to connect to the server with retries"""
    global connected
    
    retries = 0
    while retries < max_retries:
        try:
            print(f"Attempting to connect to frontend at {url} (attempt {retries+1}/{max_retries})")
            sio.connect(url)
            return True
        except Exception as e:
            retries += 1
            if retries < max_retries:
                print(f"Connection failed: {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to connect after {max_retries} attempts: {e}")
                print("Make sure the frontend server is running first.")
                return False

if __name__ == "__main__":
    # Set initial start time for time-series data
    start_time = time.time()
    
    try:
        # Connect to the frontend Socket.IO server with retry logic
        frontend_url = 'http://localhost:8501'
        if connect_with_retry(frontend_url):
            print("Connection established. Sending data...")
            send_data()
        else:
            print("Could not connect to frontend. Exiting.")
    except KeyboardInterrupt:
        print("\nBackend shutting down...")
    finally:
        if sio.connected:
            sio.disconnect()