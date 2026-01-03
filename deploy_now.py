import subprocess
import os

def deploy():
    key_path = os.path.join(os.path.expanduser('~'), '.ssh', 'Keyzinha.pem')
    
    ssh_cmd = [
        "ssh", 
        "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "ec2-user@danielmello.store",
        "cd Lanches-da-Op && sudo chown -R ec2-user:ec2-user . && git fetch origin && git reset --hard origin/main && source venv/bin/activate && python extra_files/update_production_schema.py && sudo systemctl restart lanches-da-op"
    ]
    
    print("Deploying to Production...")
    try:
        subprocess.run(ssh_cmd, check=True)
        print("SUCCESS: Deployed and Restarted.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    deploy()
