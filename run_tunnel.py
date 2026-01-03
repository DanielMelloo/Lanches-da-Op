import subprocess
import os
import sys
import time
import threading

def run():
    key_path = os.path.join(os.path.expanduser('~'), '.ssh', 'Keyzinha.pem')
    
    cmd = [
        "ssh", 
        "-i", key_path,
        "-N",
        "-L", "3307:127.0.0.1:3306",
        "-o", "ServerAliveInterval=60",
        "-o", "StrictHostKeyChecking=no",
        "ec2-user@danielmello.store"
    ]
    
    print(f"--- Starting System SSH Tunnel ---")
    
    if not os.path.exists(key_path):
        print(f"ERROR: Key file not found at {key_path}")
        return

    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1
        )
        
        print("Tunnel process started.")
        print("Listening on 127.0.0.1:3307 -> Remote 3306")
        
        # Thread to read output without blocking logic in main loop
        def log_output():
             try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(line.strip())
                    else:
                        break
             except Exception as e:
                 # This can happen if pipe closes
                 pass

        t = threading.Thread(target=log_output, daemon=True)
        t.start()
        
        # Monitor Loop
        while True:
            ret = process.poll()
            if ret is not None:
                print(f"Tunnel exited with code {ret}")
                break
            time.sleep(1)
            
    except Exception as e:
        print(f"Error launching ssh: {e}")

if __name__ == "__main__":
    run()
