import customtkinter as ctk
import subprocess
import threading
import queue
import os
import sys
import tkinter as tk
from ctypes import windll
from PIL import Image

# --- Configuration ---
PROJECT_DIR = r"d:\Prog\Novo Lanches OP"
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
SCRIPTS = {
    "Tunnel SSH": "run_tunnel.py",
    "WhatsApp Bot": "local_whatsapp_dispatcher.py",
    "Menu Scraper": "worker_local.py"
}

# --- Theme ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green") # Neon Green vibe

class BotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup (Frameless)
        self.overrideredirect(True) 
        self.geometry("600x720")
        self.configure(fg_color="#0f1115") # Match Web App Dark BG
        
        # Center Window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width/2) - (600/2)
        y = (screen_height/2) - (720/2)
        self.geometry(f"600x720+{int(x)}+{int(y)}")

        # Make Taskbar Icon Visible (Windows Hack)
        self.after(10, self.set_app_window)

        # Ensure working dir
        if os.path.exists(PROJECT_DIR):
            os.chdir(PROJECT_DIR)

        # State
        self.processes = {}
        self.log_queues = {}
        self.ui_cards = {}
        
        # --- Custom Title Bar ---
        self.title_bar = ctk.CTkFrame(self, height=40, fg_color="#1a1d26", corner_radius=0)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.bind("<Button-1>", self.get_pos)
        self.title_bar.bind("<B1-Motion>", self.move_window)
        
        self.app_title = ctk.CTkLabel(self.title_bar, text="Lanches Bots Control", 
                                     font=("Segoe UI", 12, "bold"), text_color="#ccc")
        self.app_title.pack(side="left", padx=15)
        
        # Close Button
        self.btn_close = ctk.CTkButton(self.title_bar, text="✕", width=40, height=40,
                                      fg_color="transparent", hover_color="#c42b1c", 
                                      text_color="#fff", corner_radius=0,
                                      command=self.on_closing)
        self.btn_close.pack(side="right")
        
        # Minimize Button
        self.btn_min = ctk.CTkButton(self.title_bar, text="─", width=40, height=40,
                                    fg_color="transparent", hover_color="#333", 
                                    text_color="#fff", corner_radius=0,
                                    command=self.minimize_window)
        self.btn_min.pack(side="right")

        # --- Main Content ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header Info
        self.header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header.pack(fill="x", mb=20)
        
        ctk.CTkLabel(self.header, text="Dashboard", font=("Segoe UI", 24, "bold"), text_color="#fff").pack(anchor="w")
        ctk.CTkLabel(self.header, text="Gerencie os processos de automação", font=("Segoe UI", 13), text_color="#666").pack(anchor="w")

        # Scroll Area
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True)

        # Footer
        self.footer = ctk.CTkLabel(self, text="v2.5 • Developed by Daniel Mello", 
                                  font=("Segoe UI", 10), text_color="#444", height=30)
        self.footer.pack(side="bottom", fill="x", pady=5)

        # Create Cards
        for name, script in SCRIPTS.items():
            self.create_card(name, script)

        # Loop
        self.check_queues()

    def set_app_window(self):
        # Force window to appear in taskbar
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        hwnd = windll.user32.GetParent(self.winfo_id())
        style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        self.wm_withdraw()
        self.after(10, self.wm_deiconify)

    def get_pos(self, event):
        self.xwin = self.winfo_x()
        self.ywin = self.winfo_y()
        self.startx = event.x_root
        self.starty = event.y_root

    def move_window(self, event):
        self.geometry(f"+{self.xwin + (event.x_root - self.startx)}+{self.ywin + (event.y_root - self.starty)}")
        
    def minimize_window(self):
        self.iconify()

    def create_card(self, name, script):
        self.log_queues[name] = queue.Queue()
        
        # Card Frame (Glass Effect Sim)
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#1a1d26", corner_radius=12, border_width=1, border_color="#2a2d36")
        card.pack(fill="x", pady=8, ipady=5)

        # Top Row
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=15)

        # Status Dot
        status_canvas = ctk.CTkCanvas(top, width=10, height=10, bg="#1a1d26", highlightthickness=0)
        status_canvas.pack(side="left", padx=(0, 12))
        status_id = status_canvas.create_oval(1, 1, 9, 9, fill="#444", outline="")

        # Title
        title_lbl = ctk.CTkLabel(top, text=name, font=("Segoe UI", 15, "bold"), text_color="#eee")
        title_lbl.pack(side="left")

        # Buttons
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="right")

        btn_start = ctk.CTkButton(btn_frame, text="▶ INICIAR", width=90, height=32, 
                                 fg_color="#00C853", hover_color="#00E676",
                                 font=("Segoe UI", 11, "bold"), text_color="#000",
                                 command=lambda: self.start_process(name, script))
        btn_start.pack(side="left", padx=5)

        btn_stop = ctk.CTkButton(btn_frame, text="⏹ PARAR", width=90, height=32, 
                                fg_color="#2a2d36", hover_color="#c42b1c", text_color="#888",
                                font=("Segoe UI", 11, "bold"), state="disabled",
                                command=lambda: self.stop_process(name))
        btn_stop.pack(side="left", padx=5)
        
        # Log Toggle
        btn_log = ctk.CTkButton(btn_frame, text="LOGS", width=50, height=32,
                               fg_color="transparent", border_width=1, border_color="#333", text_color="#888",
                               hover_color="#333", font=("Segoe UI", 10),
                               command=lambda: self.toggle_logs(name))
        btn_log.pack(side="left", padx=(10, 0))

        # Log Area (Hidden) - Terminal Style
        log_frame = ctk.CTkFrame(card, fg_color="#000", corner_radius=6)
        # Not packed yet
        
        log_box = ctk.CTkTextbox(log_frame, height=180, fg_color="transparent", text_color="#0f0", 
                                font=("Consolas", 10), activate_scrollbars=True)
        log_box.pack(fill="both", expand=True, padx=5, pady=5)

        self.ui_cards[name] = {
            "status_canvas": status_canvas,
            "status_id": status_id,
            "btn_start": btn_start,
            "btn_stop": btn_stop,
            "log_box": log_box,
            "log_frame": log_frame,
            "log_visible": False
        }

    def toggle_logs(self, name):
        ui = self.ui_cards[name]
        if ui["log_visible"]:
            ui["log_frame"].pack_forget()
            ui["log_visible"] = False
        else:
            ui["log_frame"].pack(fill="x", padx=15, pady=(0, 15))
            ui["log_visible"] = True

    def start_process(self, name, script):
        if name in self.processes and self.processes[name].poll() is None: return

        ui = self.ui_cards[name]
        q = self.log_queues[name]
        
        try:
            if not os.path.exists(VENV_PYTHON):
                q.put(f"Python missing: {VENV_PYTHON}\n")
                return

            cmd = [VENV_PYTHON, "-u", script]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=PROJECT_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
            self.processes[name] = proc
            
            # UI Running State
            ui["status_canvas"].itemconfig(ui["status_id"], fill="#00ff88") # Bright Green
            ui["btn_start"].configure(state="disabled", fg_color="#222", text_color="#555")
            ui["btn_stop"].configure(state="normal", fg_color="#c42b1c", text_color="#fff")
            
            t = threading.Thread(target=self.read_output, args=(name, proc, q), daemon=True)
            t.start()
            q.put(f"> Starting {script}...\n")
            
            # Auto-open logs for some
            if name == "Tunnel SSH" and not ui["log_visible"]:
                 self.toggle_logs(name)
                 
        except Exception as e:
            q.put(f"[Error] {e}\n")

    def stop_process(self, name):
        proc = self.processes.get(name)
        if proc:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=1)
                except: proc.kill()
            del self.processes[name]

        ui = self.ui_cards[name]
        ui["status_canvas"].itemconfig(ui["status_id"], fill="#444")
        ui["btn_start"].configure(state="normal", fg_color="#00C853", text_color="#000")
        ui["btn_stop"].configure(state="disabled", fg_color="#2a2d36", text_color="#888")
        self.log_queues[name].put(f"\n> Stopped.\n")

    def read_output(self, name, proc, q):
        try:
            for line in iter(proc.stdout.readline, ''):
                if line: q.put(line)
                else: break
        except: pass

    def check_queues(self):
        for name, q in self.log_queues.items():
            ui = self.ui_cards[name]
            box = ui["log_box"]
            while not q.empty():
                try:
                    msg = q.get_nowait()
                    box.configure(state="normal")
                    box.insert("end", msg)
                    box.see("end")
                    box.configure(state="disabled")
                except queue.Empty: break
                
        for name, proc in list(self.processes.items()):
            if proc.poll() is not None:
                self.stop_process(name)

        self.after(100, self.check_queues)

    def on_closing(self):
        for name in list(self.processes.keys()):
            self.stop_process(name)
        self.destroy()

if __name__ == "__main__":
    app = BotApp()
    app.mainloop()
