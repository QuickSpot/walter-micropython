import curses
import time
import os
import subprocess
import threading
import queue
import signal
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CMD_FILE = os.path.join(SCRIPT_DIR, 'cmd')

class ModemUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.output_queue = queue.Queue()
        self.output_lines = []
        self.command = ""
        self.command_status = ""
        self.running = True
        
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Status bar
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # Commands
        curses.init_pair(3, curses.COLOR_RED, -1)    # Errors
        
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
            return "ERROR"

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
            self.command_status = "Sent INTERRUPT signal. Exiting..."
            self.refresh_screen()
            time.sleep(1)  # Give time to see the message
        except Exception as e:
            self.command_status = f"Error sending INTERRUPT: {str(e)}"
            self.refresh_screen()
            time.sleep(1)
        
        self.running = False
    
    def start_modem_process(self):
        try:
            self.output_queue.put("Starting modem process...")
            
            proc = subprocess.Popen(
                ['mpremote', 'mount', '.', '+', 'run', 'modem_pass_through.py'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=SCRIPT_DIR
            )
            
            for line in proc.stdout:
                if not self.running:
                    break
                self.output_queue.put(line.strip())
            
            proc.stdout.close()
            proc.wait()
            
            self.output_queue.put("Modem process terminated.")
        except Exception as e:
            self.output_queue.put(f"Error in modem process: {str(e)}")
    
    def process_command(self):
        if not self.command:
            return
            
        current_flag = self.read_cmd_file()
        if current_flag == "READ":
            if self.write_cmd_file(self.command):
                self.command_status = f"Command sent: {self.command}"
            else:
                self.command_status = "Failed to write command!"
        else:
            self.command_status = f"Waiting: CMD file not in READ state (current: {current_flag})"
        
        self.command = ""
    
    def refresh_screen(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Status bar at the top
        current_flag = self.read_cmd_file()
        status = "READY" if current_flag == "READ" else f"WAITING ({current_flag})"
        status_line = f" Status: {status} | Press Ctrl+C or ESC to exit "
        self.stdscr.addstr(0, 0, status_line.ljust(width), curses.color_pair(1))
        
        # Output area: reserve space for the status line, output area, command status, and input prompt.
        output_height = height - 4  # (line 0: top status, line height-2: command status, line height-1: input)
        visible_lines = self.output_lines[-output_height:] if self.output_lines else []
        
        for i, line in enumerate(visible_lines):
            if i < output_height:
                if "Error" in line or "Failed" in line:
                    self.stdscr.addstr(i + 1, 0, line[:width-1], curses.color_pair(3))
                else:
                    self.stdscr.addstr(i + 1, 0, line[:width-1])
        
        self.stdscr.addstr(height - 2, 0, self.command_status.ljust(width), curses.color_pair(2) if 'sent' in self.command_status else curses.color_pair(3))
        
        prompt = "Command: "
        self.stdscr.addstr(height - 1, 0, prompt)
        self.stdscr.addstr(height - 1, len(prompt), self.command[:width-len(prompt)-1])
        
        self.stdscr.move(height - 1, len(prompt) + len(self.command))
        
        self.stdscr.refresh()
    
    def run(self):
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
        print("Sent INTERRUPT signal before exiting.")
    except:
        pass
    
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        curses.wrapper(lambda stdscr: ModemUI(stdscr).run())
    except Exception as e:
        print(f"Error: {str(e)}")
        try:
            with open(CMD_FILE, 'w') as f:
                f.write('INTERRUPT')
            print("Sent INTERRUPT signal before exiting.")
        except:
            pass

if __name__ == "__main__":
    main()
