import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess
import threading
import queue
import os
import signal
import sys
import time

# --- Configuration ---
PROJECT_DIR = r"d:\Prog\Novo Lanches OP"
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")

THEME = {
    "bg": "#121212",           # Main Window Background (Deep Dark)
    "card_bg": "#1E1E1E",      # Card Background
    "fg_primary": "#E0E0E0",   # Primary Text
    "fg_secondary": "#A0A0A0", # Secondary Text (Logs/Labels)
    "accent": "#BB86FC",       # Accent Color (Purple)
    "success": "#03DAC6",      # Teal for Success/Running
    "danger": "#CF6679",       # Red for Stop/Error
    "log_bg": "#000000",       # Log Terminal Background
    "log_fg": "#00FF00",       # Log Text
    "button_default": "#333333",
    "button_hover": "#444444"
}

SCRIPTS = {
    "Production Tunnel": "run_tunnel.py",
    "WhatsApp Dispatcher": "local_whatsapp_dispatcher.py",
    "Menu Scraper": "worker_local.py"
}

class ModernButton(tk.Button):
    """Custom Flat Button with Hover Effect"""
    def __init__(self, master, **kwargs):
        self.default_bg = kwargs.get("bg", THEME["button_default"])
        self.hover_bg = kwargs.pop("hover_bg", THEME["button_hover"])
        self.text_color = kwargs.get("fg", THEME["fg_primary"])
        
        kwargs["relief"] = "flat"
        kwargs["activebackground"] = self.hover_bg
        kwargs["activeforeground"] = self.text_color
        kwargs["borderwidth"] = 0
        kwargs["cursor"] = "hand2"
        kwargs["pady"] = 5
        kwargs["padx"] = 15
        
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.hover_bg

    def on_leave(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.default_bg
            
class StatusIndicator(tk.Canvas):
    """Canvas drawing a circle to indicate status"""
    def __init__(self, master, size=14, **kwargs):
        # Allow bg override, set default if missing
        if "bg" not in kwargs:
            kwargs["bg"] = THEME["card_bg"]
            
        super().__init__(master, width=size, height=size, highlightthickness=0, **kwargs)
        self.size = size
        self.indicator = self.create_oval(2, 2, size-2, size-2, fill="#555555", outline="")
    
    def set_status(self, status):
        color = "#555555" # Stopped/Gray
        if status == "RUNNING":
            color = THEME["success"]
        elif status == "STOPPING":
            color = THEME["danger"]
        elif status == "STARTING":
            color = THEME["accent"]
            
        self.itemconfig(self.indicator, fill=color)

class BotManagerApp:
    def __init__(self, root):
        self.root = root
        
        # Ensure we are in the project dir
        if os.path.exists(PROJECT_DIR):
            os.chdir(PROJECT_DIR)
            
        self.root.title("Lanches da OP - Bot Manager")
        self.root.geometry("550x700")
        self.root.configure(bg=THEME["bg"])
        
        # Custom Fonts
        self.font_header = ("Segoe UI", 16, "bold")
        self.font_title = ("Segoe UI", 11, "bold")
        self.font_ui = ("Segoe UI", 10)
        self.font_log = ("Consolas", 9)
        
        # Process Handles
        self.processes = {}
        self.log_queues = {}
        self.ui_elements = {}

        self.setup_ui()
        
        # Periodic check for queue updates
        self.root.after(100, self.process_queues)
        
        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # -- Header --
        header_frame = tk.Frame(self.root, bg=THEME["bg"], pady=20)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="Lanches Bots", font=self.font_header, 
                 bg=THEME["bg"], fg=THEME["fg_primary"]).pack()
        tk.Label(header_frame, text="Manager & Tunnel Control", font=("Segoe UI", 9), 
                 bg=THEME["bg"], fg=THEME["fg_secondary"]).pack()

        # -- Scrollable Container (for many bots) --
        # Simple implementation: just a main frame for now as we have few items
        container = tk.Frame(self.root, bg=THEME["bg"], padx=25)
        container.pack(fill="both", expand=True)

        for name, script in SCRIPTS.items():
            self.create_bot_card(container, name, script)
            
        # -- Footer --
        footer = tk.Label(self.root, text="v2.0 • Running on Python 3.11", 
                          font=("Segoe UI", 8), bg=THEME["bg"], fg="#444444", pady=10)
        footer.pack(fill="x", side="bottom")

    def create_bot_card(self, parent, name, script):
        self.log_queues[name] = queue.Queue()
        
        # Card Frame (Rounded look simulating via distinct background)
        card = tk.Frame(parent, bg=THEME["card_bg"], pady=10, padx=15)
        card.pack(fill="x", pady=8)
        
        # Top Row: Status + Name + Controls
        top_row = tk.Frame(card, bg=THEME["card_bg"])
        top_row.pack(fill="x")
        
        # Status Dot
        status_ind = StatusIndicator(top_row, bg=THEME["card_bg"])
        status_ind.pack(side="left", padx=(0, 10))
        
        # Name Label
        name_lbl = tk.Label(top_row, text=name, font=self.font_title, 
                           bg=THEME["card_bg"], fg=THEME["fg_primary"])
        name_lbl.pack(side="left")
        
        # Controls Frame (Right aligned)
        controls = tk.Frame(top_row, bg=THEME["card_bg"])
        controls.pack(side="right")
        
        btn_start = ModernButton(controls, text="START", 
                                bg=THEME["button_default"], hover_bg="#2E7D32") # Dark Green Hover
        btn_start.configure(command=lambda: self.start_bot(name, script))
        btn_start.pack(side="left", padx=5)
        
        btn_stop = ModernButton(controls, text="STOP", 
                               bg=THEME["button_default"], hover_bg=THEME["danger"], state="disabled")
        btn_stop.configure(command=lambda: self.stop_bot(name))
        btn_stop.pack(side="left", padx=5)
        
        # Logs Toggle (Small)
        btn_log = tk.Label(top_row, text="Logs ▼", font=("Segoe UI", 8), 
                          bg=THEME["card_bg"], fg="#666666", cursor="hand2")
        
        # Log Area (Hidden by default)
        log_frame = tk.Frame(card, bg=THEME["card_bg"], pady=5)
        log_text = scrolledtext.ScrolledText(log_frame, height=8, bg=THEME["log_bg"], 
                                            fg=THEME["log_fg"], font=self.font_log, 
                                            state="disabled", borderwidth=0)
        log_text.pack(fill="both", expand=True)

        # Toggle Logic
        def toggle_logs(e=None):
            if log_frame.winfo_ismapped():
                log_frame.pack_forget()
                btn_log.config(text="Logs ▼", fg="#666666")
            else:
                log_frame.pack(fill="x",  pady=(10, 0))
                btn_log.config(text="Logs ▲", fg=THEME["accent"])

        btn_log.bind("<Button-1>", toggle_logs)
        btn_log.pack(side="right", padx=(10, 0))
        
        # Default open logs for Tunnel? No, minimalist means hidden.
        # But for Tunnel, seeing "Listening" is good. 
        # Let's open logs strictly for Tunnel on start.
        if "Tunnel" in name:
            toggle_logs() 
            
        self.ui_elements[name] = {
            "status_ind": status_ind,
            "btn_start": btn_start,
            "btn_stop": btn_stop,
            "log_text": log_text,
            "log_frame": log_frame
        }

    def log(self, name, message):
        q = self.log_queues.get(name)
        if q:
            q.put(message)

    def process_queues(self):
        for name, q in self.log_queues.items():
            if name not in self.ui_elements: continue
            
            ui = self.ui_elements[name]
            text_widget = ui["log_text"]
            
            while not q.empty():
                try:
                    # Smart Scroll
                    was_at_bottom = False
                    try:
                         if text_widget.yview()[1] >= 0.99:
                             was_at_bottom = True
                    except:
                        was_at_bottom = True

                    msg = q.get_nowait()
                    text_widget.config(state="normal")
                    text_widget.insert("end", msg)
                    
                    if was_at_bottom:
                        text_widget.see("end")
                        
                    text_widget.config(state="disabled")
                except queue.Empty:
                    break
        
        # Check process health
        for name, proc in list(self.processes.items()):
            if proc.poll() is not None:
                self.stop_bot(name, force_ui_only=True)
                self.log(name, f"\n[System] Process exited with code {proc.returncode}\n")

        self.root.after(100, self.process_queues)

    def start_bot(self, name, script):
        if name in self.processes and self.processes[name].poll() is None:
            return

        ui = self.ui_elements[name]
        try:
            if not os.path.exists(VENV_PYTHON):
                self.log(name, f"Error: Python not found at {VENV_PYTHON}\n")
                return

            cmd = [VENV_PYTHON, "-u", script]
            
            # Start Process
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=PROJECT_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.processes[name] = proc
            
            # Thread for reading
            t = threading.Thread(target=self.read_process_output, args=(name, proc), daemon=True)
            t.start()
            
            # UI Updates
            ui["status_ind"].set_status("RUNNING")
            ui["btn_start"].config(state="disabled", bg="#222222") # Dimmed
            ui["btn_stop"].config(state="normal", bg=THEME["button_default"]) 
            self.log(name, f"--- Started {script} ---\n")

        except Exception as e:
            self.log(name, f"Failed to start: {e}\n")

    def stop_bot(self, name, force_ui_only=False):
        if not force_ui_only:
            proc = self.processes.get(name)
            if proc and proc.poll() is None:
                self.log(name, "Stopping...\n")
                if "run_tunnel.py" in str(proc.args):
                     # SSH needs kill
                     proc.kill()
                else:
                    proc.terminate()
                
                try:
                    proc.wait(timeout=2)
                except:
                    proc.kill()
        
        if name in self.processes and not force_ui_only:
            del self.processes[name]

        ui = self.ui_elements[name]
        ui["status_ind"].set_status("STOPPED")
        ui["btn_start"].config(state="normal", bg=THEME["button_default"])
        ui["btn_stop"].config(state="disabled", bg="#222222")

    def read_process_output(self, name, proc):
        # Dedicated thread to read stdout
        try:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    self.log(name, line)
                else: 
                    break 
        except:
            pass

    def on_close(self):
        for name in list(self.processes.keys()):
            self.stop_bot(name)
        self.root.destroy()

if __name__ == "__main__":
    if os.name == 'nt':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    root = tk.Tk()
    app = BotManagerApp(root)
    root.mainloop()
