import subprocess
import sys
import time

# get the python executable
# expects the venv to be active
python_env = sys.executable
print(python_env)

frontend_app = "app/dash_app/frontend_app.py"
streaming_client = "app/dash_app/data_streaming_client.py"

try:
    print(f"Starting {frontend_app}...")
    frontend_process = subprocess.Popen([python_env, frontend_app])

    print(f"Starting {streaming_client}...")
    client_process = subprocess.Popen([python_env, streaming_client])

    # Keep the script running while the subprocesses are active
    while True:
        # Check if either process has terminated unexpectedly
        frontend_returncode = frontend_process.poll()
        client_returncode = client_process.poll()

        if frontend_returncode is not None:
            print(f"{frontend_app} terminated with return code {frontend_returncode}.")
            break

        if client_returncode is not None:
            print(f"{streaming_client} terminated with return code {client_returncode}.")
            break

        # time.sleep(0.1)

except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected; terminating processes...")

    # Terminate both processes
    frontend_process.terminate()
    client_process.terminate()

    # Wait for processes to terminate
    frontend_process.wait()
    client_process.wait()

    print("Processes terminated. Exiting")

finally:
    # Ensure processes are cleaned up if still running
    if frontend_process.poll() is None:  # Check if the process is still running
        frontend_process.terminate()
    if client_process.poll() is None:
        client_process.terminate()

    print("\nCleanup complete. Goodbye!")
