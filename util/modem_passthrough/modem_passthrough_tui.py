import curses
import time
import os
import subprocess
import threading
import queue
import signal
import sys
import shutil

from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CMD_FILE = os.path.join(SCRIPT_DIR, 'cmd')
LOG_FILE = os.path.join(SCRIPT_DIR, 'passthrough.log')

class ModemUI:
    def __init__(self, stdscr):
        self.logging = '--log' in sys.argv
        self.stdscr = stdscr
        self.output_queue = queue.Queue()
        self.output_lines = []
        self.command = ''
        self.command_result = ''
        self.running = True
        self.passthrough_state = 'STARTING'
        
        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)

        self.colors = {
            'top_header': {
                'STARTING': 2,
                'READY': 1,
                'WAITING': 2,
                'ERROR': 3,
                'NO': 3
            },
            'out_lines': {
                'OK': 4,
                'ERROR': 5
            }
        }
        
        curses.curs_set(1)  # Show cursor
        self.stdscr.nodelay(True)  # Non-blocking input
        
        self.modem_thread = threading.Thread(
            target=self.start_modem_process,
            daemon=True
        )
        self.modem_thread.start()
    
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
                if content == 'READ':
                    f.seek(0)
                    f.write(command)
                    f.truncate()
                    return True
                else:
                    return False
        except Exception:
            return False
    
    def send_interrupt_and_exit(self):
        try:
            with open(CMD_FILE, 'w') as f:
                f.write('INTERRUPT')
            self.command_result = 'Sent INTERRUPT signal. Exiting...'
        except Exception as e:
            self.command_result = f'Error sending INTERRUPT: {str(e)}'
            self.passthrough_state = 'ERROR'
            self.refresh_screen()
            time.sleep(3)
        
        self.running = False

    def log(self, line: str, meta: str = None, raw=False):
        with open(LOG_FILE, 'a+') as f:
            if raw:
                f.write(line)
            else:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f'[{timestamp}] {meta:>7}: {line.strip()}\n'
                f.write(log_entry)
    
    def start_modem_process(self):
        try:
            self.output_queue.put('[i] >> Starting modem process...')
            cmd_variants = [
                ['mpremote'],
                ['python', '-m', 'mpremote'],
                ['python3', '-m', 'mpremote']
            ]
            cmd = None
            for variant in cmd_variants:
                if shutil.which(variant[0]):
                    cmd = variant
                    break
            if cmd is None:
                raise FileNotFoundError(
                    'mpremote command not found. Ensure it is installed and accessible.'
                )
            
            proc = subprocess.Popen(
                cmd + ['mount', '.', '+', 'run', 'esp-script.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=SCRIPT_DIR
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
    
    def process_command(self):
        if not self.command:
            return
        elif self.command in ['INTERRUPT', 'READ', 'PROGFAIL', 'TUI-ERROR']:
            self.command_result = f'Command not allowed; INTERRUPT, READ, PROGFAIL & TUI-ERROR are reserved'
            return
    
        if self.passthrough_state == 'READY' and self.read_cmd_file() == 'READ':
            if self.write_cmd_file(self.command):
                self.command_result = f'Sent: {self.command}'
                self.passthrough_state = f'WAITING ({self.command})'

                if self.logging:
                    self.log(line=self.command, meta='command')
            else:
                self.command_result = 'Failed to write command!'
                self.passthrough_state = f'ERROR ({self.command})'
        else:
            self.command_result = f'Passthrough not ready! Command not sent.'
        
        self.command = ''
    
    def refresh_screen(self):
        if self.passthrough_state != 'READY':
            self.update_passthrough_state()

        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        status = f' Status: {self.passthrough_state}'
        top_header_info = f' |{' Logging Enabled |' if self.logging else ''} Press Ctrl+C to exit'.ljust(width - len(status))

        self.stdscr.addstr(
            0, 0,
            status,
            curses.color_pair(
                self.colors['top_header'][self.passthrough_state.split(maxsplit=1)[0]]
            ) | curses.A_BOLD
        )
        
        self.stdscr.addstr(
            0, + len(status),
            top_header_info,
            curses.color_pair(self.colors['top_header'][self.passthrough_state.split(maxsplit=1)[0]])
        )
        

        output_height = height - 5
        visible_lines = self.output_lines[-output_height:] if self.output_lines else []
        
        for i, line in enumerate(visible_lines):
            if i < output_height:
                if 'ERROR' in line:
                    self.stdscr.addstr(i + 1, 0, line[:width-1],
                                       curses.color_pair(self.colors['out_lines']['ERROR']))
                elif 'OK' in line:
                    self.stdscr.addstr(i + 1, 0, line[:width-1],
                                       curses.color_pair(self.colors['out_lines']['OK']))
                elif '[i] >> ' in line:
                    self.stdscr.addstr(i + 1, 0, line[:width-1],
                                       curses.A_DIM)
                else:
                    self.stdscr.addstr(i + 1, 0, line[:width-1])
        
        self.stdscr.addstr(height - 2, 0, self.command_result.ljust(width), curses.A_DIM)
        
        prompt = 'Command: '
        self.stdscr.addstr(height - 1, 0, prompt, curses.A_BOLD)
        self.stdscr.addstr(height - 1, len(prompt), self.command[:width-len(prompt)-1])
        
        self.stdscr.move(height - 1, len(prompt) + len(self.command))
        
        self.stdscr.refresh()

    def update_passthrough_state(self):
        cmd_file_content = self.read_cmd_file()
        if cmd_file_content == 'PROGFAIL':
            self.passthrough_state == 'NO COMM'
        if self.passthrough_state != 'NO COMM' and self.passthrough_state != 'STARTING':
            if cmd_file_content == 'READ':
                self.passthrough_state = 'READY'
            elif cmd_file_content == 'TUI-ERROR':
                self.passthrough_state = 'ERROR'

    def run(self):
        self.update_passthrough_state()

        if self.logging:
            self.log(line='===== PROGRAM STARTED =====\r\n', raw=True)

        while self.running:
            try:
                while not self.output_queue.empty():
                    line = self.output_queue.get_nowait()
                    self.output_lines.append(line)
            except Exception:
                pass

            self.refresh_screen()
            
            try:
                key = self.stdscr.getch()
                if key == curses.KEY_RESIZE:
                    # Handle terminal resize
                    self.stdscr.clear()
                elif key == 27:  # ESC
                    self.send_interrupt_and_exit()
                elif key in (10, 13):  # Enter
                    self.process_command()
                elif key in (127, 8) or key == curses.KEY_BACKSPACE:  # Backspace
                    self.command = self.command[:-1]
                elif key != -1 and 32 <= key <= 126:  # Printable characters
                    self.command += chr(key)
            except Exception:
                pass
            
            time.sleep(0.05)

def signal_handler(sig, frame):
    try:
        with open(CMD_FILE, 'w') as f:
            f.write('INTERRUPT')
        print('Sent INTERRUPT signal before exiting.')
    except:
        pass
    
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        curses.wrapper(lambda stdscr: ModemUI(stdscr).run())
    except Exception as e:
        print(f'Error: ', e)
        try:
            with open(CMD_FILE, 'w') as f:
                f.write('INTERRUPT')
            print('Sent INTERRUPT signal before exiting.')
        except:
            pass

if __name__ == '__main__':
    main()