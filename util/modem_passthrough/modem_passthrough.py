import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import os
import subprocess
import shutil
import signal
import sys
import time
from datetime import datetime

# Constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CMD_FILE = os.path.join(SCRIPT_DIR, 'cmd')
LOG_FILE = os.path.join(SCRIPT_DIR, 'passthrough.log')
WATCH_INTERVAL_MS = 200

class ModemGUI:
    def __init__(self, root):
        self.logging = '--log' in sys.argv
        self.root = root
        self.root.title('Walter Modem Passthrough')
        self.root.configure(bg='gray10')

        # Queues & state
        self.output_queue = queue.Queue()
        self.output_lines = []
        self.running = True
        self.passthrough_state = 'STARTING'
        self.command_result = ''

        # Command history
        self.history = []
        self.history_index = None

        # Track cmd file mtime
        self._last_mtime = None

        # UI color/tag maps
        self.header_colors = {
            'STARTING': ('black', 'orange'),
            'READY':    ('black', 'lime green'),
            'WAITING':  ('black', 'orange'),
            'ERROR':    ('black', 'red2'),
            'NO':       ('black', 'red2'),
        }
        self.output_tags = {
            'ok':    {'foreground': 'lawn green'},
            'error': {'foreground': 'orange red'},
            'dim':   {'foreground': 'gray'},
            'normal':{'foreground': 'white'},
        }

        self.build_ui()
        self.bind_events()

        # Poll cmd file
        self.root.after(WATCH_INTERVAL_MS, self.watch_cmd_file)

        # Background mpremote process
        self.modem_thread = threading.Thread(target=self.start_modem_process, daemon=True)
        self.modem_thread.start()

    def build_ui(self):
        self.header_label = tk.Label(
            self.root, 
            text='', 
            font=('Courier New', 12, 'bold'), 
            anchor='w'
        )
        self.header_label.pack(fill=tk.X)

        self.output_text = tk.Text(
            self.root,
            font=('Courier New', 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg='gray10'
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for tag, opts in self.output_tags.items():
            self.output_text.tag_config(tag, **opts)

        self.command_status_label = tk.Label(
            self.root,
            text='',
            font=('Courier New', 10, 'italic'),
            anchor='w'
        )
        self.command_status_label.pack(fill=tk.X)

        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(fill=tk.X)
        prompt = tk.Label(
            self.input_frame,
            text='Command: ',
            font=('Courier New', 10, 'bold')
        )
        prompt.pack(side=tk.LEFT, padx=5)
        
        self.command_entry = tk.Entry(self.input_frame, font=('Courier New', 10))
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def bind_events(self):
        self.root.bind('<Escape>', lambda e: self.send_interrupt_and_exit())
        self.root.protocol('WM_DELETE_WINDOW', self.send_interrupt_and_exit)
        signal.signal(signal.SIGINT,  lambda s,f: self.send_interrupt_and_exit())
        signal.signal(signal.SIGTERM, lambda s,f: self.send_interrupt_and_exit())

        self.command_entry.bind('<Return>', lambda e: self.process_command())
        self.command_entry.bind('<Up>',     lambda e: self._history_prev())
        self.command_entry.bind('<Down>',   lambda e: self._history_next())

    def watch_cmd_file(self):
        """
        Poll CMD_FILE mtime; schedule UI refresh on change.
        """
        try:
            mtime = os.path.getmtime(CMD_FILE)
        except Exception:
            mtime = None

        if self._last_mtime is None:
            self._last_mtime = mtime
        elif mtime != self._last_mtime:
            self._last_mtime = mtime
            self.schedule_refresh()

        if self.running:
            self.root.after(WATCH_INTERVAL_MS, self.watch_cmd_file)

    def schedule_refresh(self):
        self.root.after(0, self.refresh_ui)

    def update_passthrough_state(self):
        content = self.read_cmd_file()
        if content == 'PROGFAIL':
            self.passthrough_state = 'NO COMM'
        elif self.passthrough_state not in ['NO COMM', 'STARTING']:
            if content == 'READ':
                self.passthrough_state = 'READY'
            elif content == 'TUI-ERROR':
                self.passthrough_state = 'ERROR'

    def refresh_ui(self):
        self.update_passthrough_state()
        
        while not self.output_queue.empty():
            try:
                ln = self.output_queue.get_nowait()
                self.output_lines.append(ln)
            except queue.Empty:
                break

        try:
            visible = max(5, self.output_text.winfo_height() // 15)
        except:
            visible = 20
        display = self.output_lines[-visible:]

        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        for line in display:
            if 'ERROR' in line:
                tag = 'error'
            elif 'OK' in line:
                tag = 'ok'
            elif line.startswith('[i] >>'):
                tag = 'dim'
            else:
                tag = 'normal'
            self.output_text.insert(tk.END, line + '\n', tag)

        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END)

        # Header & status
        header = f' Status: {self.passthrough_state}'
        if self.logging:
            header += ' | Logging Enabled'
        h_fg, h_bg = self.header_colors.get(self.passthrough_state.split()[0], ('black','white'))
        self.header_label.config(text=header, fg=h_fg, bg=h_bg)
        
        if ('Reserved' in self.command_result or
        'Failed to send' in self.command_result or
        'Not ready' in self.command_result):
            cs_fg = 'firebrick3'
        else:
            cs_fg = 'black'
        self.command_status_label.config(text=self.command_result, fg=cs_fg)

    def start_modem_process(self):
        try:
            self.output_queue.put('[i] >> Starting modem process...')
            self.schedule_refresh()

            variants = [['mpremote'], ['python','-m','mpremote'], ['python3','-m','mpremote']]
            cmd = next((v for v in variants if shutil.which(v[0])), None)
            if not cmd:
                raise FileNotFoundError('mpremote not found')

            proc = subprocess.Popen(
                cmd + ['mount','.','+','run','esp-script.py'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, cwd=SCRIPT_DIR
            )

            for line in proc.stdout:
                if not self.running:
                    break
                if self.logging:
                    if 'Traceback' in line:
                        raise Exception('Underlying mpremote process crashed.')
                    elif 'mpremote: ' in line:
                        self.log(
                            line=line[10:],
                            meta='mpremote'
                        )
                    elif 'Local directory .' not in line and '[i]' not in line:
                        self.log(
                            line=line,
                            meta='modem'
                        )
                if line.strip() == '+SYSSTART': self.passthrough_state = 'READY'
                if 'mpremote:' in line: line = '[i] >> ' + line
                if 'Local directory .' not in line:
                    self.output_queue.put(line.strip())
                self.schedule_refresh()
            
            def attempt_reconnect():
                time.sleep(3)
                self.output_lines = []
                self.output_queue.put(f'[i] >> Retrying device connection...')
                self.schedule_refresh()
                self.start_modem_process()

            proc.stdout.close(); proc.wait()
            self.output_queue.put('[i] >> Modem process terminated.')
            self.passthrough_state = 'NO COMM'
            self.schedule_refresh()
            attempt_reconnect()
        except FileNotFoundError as e:
            if self.logging: self.log(line='===== PROGRAM CRASHED =====\n', raw=True)
            self.output_queue.put(f'[i] >> Error: {e}')
            self.passthrough_state = 'ERROR'
            self.schedule_refresh()
            attempt_reconnect()
        except Exception as e:
            if self.logging: self.log(line='===== PROGRAM CRASHED (Device disconnect?) =====\n', raw=True)
            self.output_queue.put(f'[i] >> Error in modem process: {e}')
            self.passthrough_state = 'NO COMM'
            self.schedule_refresh()
            time.sleep(7)
            self.start_modem_process()

    def log(self, line, meta=None, raw=False):
        try:
            with open(LOG_FILE, 'a+') as f:
                if raw:
                    f.write(line)
                else:
                    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{ts}] {meta:>9}: {line.strip()}\n")
        except:
            pass

    def read_cmd_file(self):
        try:
            return open(CMD_FILE,'r').read().strip()
        except:
            return 'TUI-ERROR'

    def write_cmd_file(self, command):
        try:
            with open(CMD_FILE,'r+') as f:
                if f.read().strip() != 'READ': return False
                f.seek(0); f.write(command); f.truncate()
            return True
        except:
            return False

    def send_interrupt_and_exit(self):
        if not self.running: return
        self.running = False
        try:
            with open(CMD_FILE,'w') as f:
                f.write('INTERRUPT')
            self.command_result = 'Sent INTERRUPT; exiting.'
        except Exception as e:
            self.command_result = f'Error sending INTERRUPT: {e}'
        self.schedule_refresh()
        if self.logging: self.log(line='===== PROGRAM STOPPED =====\n', raw=True)
        self.root.after(100, self.root.destroy)

    def process_command(self):
        cmd = self.command_entry.get().strip()
        if not cmd: return
        reserved = ['INTERRUPT','READ','PROGFAIL','TUI-ERROR']
        if cmd in reserved:
            self.root.bell()
            self.command_result = f'Reserved: {cmd}'
        elif self.passthrough_state == 'READY' and self.read_cmd_file()=='READ':
            if self.write_cmd_file(cmd):
                self.command_result = f'Sent: {cmd}'
                self.passthrough_state = f'WAITING ({cmd})'
                self.history.append(cmd); self.history_index=None
                if self.logging: self.log(line=cmd, meta='command')
            else:
                self.root.bell()
                self.command_result='Failed to send.'; self.passthrough_state=f'ERROR ({cmd})'
        else:
            self.root.bell()
            self.command_result='Not ready; command dropped.'
        self.command_entry.delete(0, tk.END)
        self.schedule_refresh()

    def _history_prev(self):
        if not self.history: return
        if self.history_index is None:
            self.history_index = len(self.history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)
        self._show_history()

    def _history_next(self):
        if self.history_index is None: return
        self.history_index += 1
        if self.history_index >= len(self.history):
            self.history_index = None
            self.command_entry.delete(0, tk.END)
        else:
            self._show_history()

    def _show_history(self):
        cmd = self.history[self.history_index]
        self.command_entry.delete(0, tk.END); self.command_entry.insert(0, cmd)

    def run(self):
        if self.logging: self.log(line='===== PROGRAM STARTED =====\n', raw=True)
        self.root.mainloop()

if __name__=='__main__':
    root=tk.Tk(); ModemGUI(root).run()
