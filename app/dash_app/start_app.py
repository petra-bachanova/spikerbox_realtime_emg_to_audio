import subprocess
import sys

# get the python executable
# expects the venv to be active
python_env = sys.executable
print(python_env)

server_and_frontend_app = "app/dash_app/server_and_frontend.py"
streaming_client = "app/dash_app/data_streaming_client.py"

try:
    print(f"Starting {server_and_frontend_app}...")
    server_frontend_process = subprocess.Popen([python_env, server_and_frontend_app])

    print(f"Starting {streaming_client}...")
    client_process = subprocess.Popen([python_env, streaming_client])

    # Keep the script running while the subprocesses are active
    while True:
        # Check if either process has terminated unexpectedly
        frontend_returncode = server_frontend_process.poll()
        client_returncode = client_process.poll()

        if frontend_returncode is not None:
            print(f"{server_and_frontend_app} terminated with return code {frontend_returncode}.")
            break

        if client_returncode is not None:
            print(f"{streaming_client} terminated with return code {client_returncode}.")
            break

except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected; terminating processes...")

    # Terminate both processes
    server_frontend_process.terminate()
    client_process.terminate()

    # Wait for processes to terminate
    server_frontend_process.wait()
    client_process.wait()

    print("Processes terminated. Exiting")

finally:
    # Ensure processes are cleaned up if still running
    if server_frontend_process.poll() is None:  # Check if the process is still running
        server_frontend_process.terminate()
    if client_process.poll() is None:
        client_process.terminate()

    print("\nCleanup complete. Goodbye!")
