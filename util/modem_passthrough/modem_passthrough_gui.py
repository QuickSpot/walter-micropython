import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import os
import subprocess
import shutil
import signal
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CMD_FILE = os.path.join(SCRIPT_DIR, 'cmd')
LOG_FILE = os.path.join(SCRIPT_DIR, 'passthrough.log')

class ModemGUI:
    def __init__(self, root):
        self.logging = '--log' in sys.argv
        self.root = root
        self.root.title('Walter Modem Passthrough')
        self.root.configure(bg='gray10')
        
        self.output_queue = queue.Queue()
        self.output_lines = []
        self.running = True
        self.passthrough_state = 'STARTING'
        self.command_result = ''
        
        self.header_colors = {
            'STARTING': ('black', 'orange'),
            'READY':    ('black', 'lime green'),
            'WAITING':  ('black', 'orange'),
            'ERROR':    ('black', 'red2'),
            'NO':  ('black', 'red2'),
        }
        self.outline_tags = {
            'ok': {'foreground': 'lawn green'},
            'error': {'foreground': 'orange red'},
            'dim': {'foreground': 'gray'},
            'normal': {'foreground': 'white'},
        }
        
        self.build_ui()
        
        self.root.bind('<Escape>', lambda event: self.send_interrupt_and_exit())
        self.root.protocol('WM_DELETE_WINDOW', self.send_interrupt_and_exit)
        signal.signal(signal.SIGINT, lambda sig, frame: self.send_interrupt_and_exit())
        signal.signal(signal.SIGTERM, lambda sig, frame: self.send_interrupt_and_exit())
        
        self.command_entry.bind('<Return>', lambda event: self.process_command())
        
        self.modem_thread = threading.Thread(target=self.start_modem_process, daemon=True)
        self.modem_thread.start()
        
        self.update_ui()
    
    def build_ui(self):
        self.header_label = tk.Label(self.root, text="", font=('Courier New', 12, 'bold'), anchor='w')
        self.header_label.pack(fill=tk.X)
        
        self.output_text = tk.Text(self.root, font=('Courier New', 10), wrap=tk.WORD, state=tk.DISABLED, bg='gray10')
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for tag, options in self.outline_tags.items():
            self.output_text.tag_config(tag, **options)
        
        # Command status label.
        self.command_status_label = tk.Label(self.root, text="", font=('Courier New', 10, 'italic'), anchor='w')
        self.command_status_label.pack(fill=tk.X)
        
        # Input frame at the bottom: prompt and Entry.
        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(fill=tk.X)
        self.prompt_label = tk.Label(self.input_frame, text='Command: ', font=('Courier New', 10, 'bold'))
        self.prompt_label.pack(side=tk.LEFT, padx=5)
        self.command_entry = tk.Entry(self.input_frame, font=('Courier New', 10))
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def update_ui(self):
        self.update_passthrough_state()
        
        while not self.output_queue.empty():
            try:
                line = self.output_queue.get_nowait()
                self.output_lines.append(line)
            except queue.Empty:
                break
        
        try:
            visible_lines = max(5, self.output_text.winfo_height() // 15)
        except Exception:
            visible_lines = 20
        display_lines = self.output_lines[-visible_lines:]
        
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        for line in display_lines:
            if 'ERROR' in line:
                tag = 'error'
            elif 'OK' in line:
                tag = 'ok'
            elif line.startswith('[i] >>'):
                tag = 'dim'
            else:
                tag = 'normal'
            self.output_text.insert(tk.END, line + "\n", tag)
        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END)
        
        header_text = f' Status: {self.passthrough_state}'
        if self.logging:
            header_text += ' | Logging Enabled'
        self.header_label.config(text=header_text)
        fg, bg = self.header_colors.get(self.passthrough_state.split(maxsplit=1)[0], ('black', 'white'))
        self.header_label.config(fg=fg, bg=bg)
        
        self.command_status_label.config(text=self.command_result)
        
        if self.running:
            self.root.after(50, self.update_ui)
    
    def start_modem_process(self):
        try:
            self.output_queue.put('[i] >> Starting modem process...')
            cmd_variants = [['mpremote'], ['python', '-m', 'mpremote'], ['python3', '-m', 'mpremote']]
            cmd = None
            for variant in cmd_variants:
                if shutil.which(variant[0]):
                    cmd = variant
                    break
            if cmd is None:
                raise FileNotFoundError('mpremote command not found. Ensure it is installed and accessible.')
            
            proc = subprocess.Popen(
                cmd + ['mount', '.', '+', 'run', 'esp-script.py'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, cwd=SCRIPT_DIR
            )
            
            for line in proc.stdout:
                if not self.running:
                    break
                if self.logging:
                    self.log(line=line, meta='output')
                if line.strip() == '+SYSSTART':
                    self.passthrough_state = 'READY'
                if 'mpremote:' in line:
                    line = '[i] >> ' + line
                self.output_queue.put(line.strip())
            
            proc.stdout.close()
            proc.wait()
            self.output_queue.put('[i] >> Modem process terminated.')
            self.passthrough_state = 'NO COMM'
        except FileNotFoundError as e:
            self.output_queue.put(f'[i] >> Error: {str(e)}')
            self.passthrough_state = 'ERROR'
        except Exception as e:
            self.output_queue.put(f'[i] >> Error in modem process: {str(e)}')
            self.passthrough_state = 'NO COMM'
    
    def log(self, line: str, meta: str = None, raw=False):
        try:
            with open(LOG_FILE, 'a+') as f:
                if raw:
                    f.write(line)
                else:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {meta:>7}: {line.strip()}\n"
                    f.write(log_entry)
        except Exception:
            pass
    
    def read_cmd_file(self):
        try:
            with open(CMD_FILE, 'r') as f:
                return f.read().strip()
        except Exception:
            return 'TUI-ERROR'
    
    def write_cmd_file(self, command):
        try:
            with open(CMD_FILE, 'r+') as f:
                content = f.read().strip()
                if content == "READ":
                    f.seek(0)
                    f.write(command)
                    f.truncate()
                    return True
                else:
                    return False
        except Exception:
            return False
    
    def send_interrupt_and_exit(self):
        if self.running:    
            self.running = False
            try:
                with open(CMD_FILE, 'w') as f:
                    f.write('INTERRUPT')
                self.command_result = 'Sent INTERRUPT signal. Exiting...'
            except Exception as e:
                self.command_result = f'Error sending INTERRUPT: {str(e)}'
                self.update_ui()
                self.root.after(3000)
            self.running = False
            self.root.destroy()
    
    def process_command(self):
        command = self.command_entry.get().strip()
        if not command:
            return
        elif command in ['INTERRUPT', 'READ', 'PROGFAIL', 'TUI-ERROR']:
            self.command_result = 'Command not allowed; INTERRUPT, READ, PROGFAIL & TUI-ERROR are reserved'
        else:
            if self.passthrough_state == 'READY' and self.read_cmd_file() == 'READ':
                if self.write_cmd_file(command):
                    self.command_result = f'Sent: {command}'
                    self.passthrough_state = f'WAITING ({command})'
                    if self.logging:
                        self.log(line=command, meta='command')
                else:
                    self.command_result = 'Failed to write command!'
                    self.passthrough_state = f'ERROR ({command})'
            else:
                self.command_result = 'Passthrough not ready! Command not sent.'
        self.command_entry.delete(0, tk.END)
    
    def update_passthrough_state(self):
        cmd_file_content = self.read_cmd_file()
        if cmd_file_content == 'PROGFAIL':
            self.passthrough_state = 'NO COMM'
        if self.passthrough_state not in ['NO COMM', 'STARTING']:
            if cmd_file_content == 'READ':
                self.passthrough_state = 'READY'
            elif cmd_file_content == 'TUI-ERROR':
                self.passthrough_state = 'ERROR'
    
    def run(self):
        self.update_passthrough_state()
        if self.logging:
            self.log(line='===== PROGRAM STARTED =====\r\n', raw=True)
        self.root.mainloop()
    
    def exit_program(self):
        self.send_interrupt_and_exit()

if __name__ == '__main__':
    root = tk.Tk()
    app = ModemGUI(root)
    app.run()