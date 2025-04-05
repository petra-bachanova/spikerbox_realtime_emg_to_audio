import subprocess

python_env = ".venv/Scripts/python"  # Path to your Python environment

# Start frontend_app.py
print("Starting frontend_app.py...")
frontend_app = "app/dash_app/frontend_app.py"
frontend_process = subprocess.Popen([python_env, frontend_app])

# Start backend_app.py
print("Starting backend_app.py...")
backend_app = "app/dash_app/flask_backend.py"
backend_process = subprocess.Popen([python_env, backend_app])

# (Optional) Wait for both processes to complete
frontend_process.wait()
backend_process.wait()

print("Both frontend and backend have completed.")
