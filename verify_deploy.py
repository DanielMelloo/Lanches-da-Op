import subprocess
import os

def check():
    key_path = os.path.join(os.path.expanduser('~'), '.ssh', 'Keyzinha.pem')
    # Check for the new action handler
    grep_cmd = "grep \"action == 'toggle_auto_send'\" Lanches-da-Op/routes_admin.py"
    
    ssh_cmd = [
        "ssh", 
        "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "ec2-user@danielmello.store",
        grep_cmd
    ]
    
    print("Verifying server code...")
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if "toggle_auto_send" in result.stdout:
            print("SUCCESS: Code found on server!")
            print(result.stdout.strip())
        else:
            print("FAILURE: Code NOT found.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
