import subprocess
import os

def check():
    key_path = os.path.join(os.path.expanduser('~'), '.ssh', 'Keyzinha.pem')
    # Command to grep for the specific logic
    grep_cmd = "grep -A 5 \"action == 'manual_dispatch'\" Lanches-da-Op/routes_admin.py"
    
    ssh_cmd = [
        "ssh", 
        "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "ec2-user@danielmello.store",
        grep_cmd
    ]
    
    print("Checking server code...")
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
