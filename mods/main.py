import json
import threading
import time
from dataclasses import dataclass
from threading import Thread
import curses
from typing import List, Dict
import socket

from socket_for_humans import Connection, Server
import textual

from src import module
from src.vars import *

@dataclass
class Config:
    net: str
    ui: str
    encryption: str
    application: str
class Chats:
    """
    сюда БДшку
    """
    def __init__(self) -> None:
        self.messages: List[Dict] = []
        self._lock = threading.Lock()

    def add_message(self, message: str, sender: str, reciver: str):
        with self._lock:
            self.messages.append({
                "sender": sender,
                "reciver": reciver,
                "msg": message,
                "time": time.time()
            })

    def update_messages(self, messages: List[Dict]) -> None:
        # merge by set of tuples to avoid duplicates, keep thread-safe
        with self._lock:
            existing = { (m["sender"], m["reciver"], m["msg"], m["time"]) for m in self.messages }
            incoming = { (m["sender"], m["reciver"], m["msg"], m["time"]) for m in messages }
            merged = existing | incoming
            # convert back to list of dicts sorted by time
            self.messages = sorted(
                [ {"sender": s, "reciver": r, "msg": msg, "time": t} for (s,r,msg,t) in merged ],
                key=lambda x: x["time"]
            )

    def snapshot(self) -> List[Dict]:
        with self._lock:
            return list(self.messages)

    def filter_by_access(self, ip: str) -> list[dict]:
        with self._lock:
            result = []
            for message in self.messages:
                if ip in (message["sender"], message["reciver"]):
                    result.append(message)
            return result

class Application(module.Module):
    def __init__(self) -> None:
        super().__init__(module_name= "MainApp", module_type= "App")

class Encryption(module.Encryption):
    def __init__(self) -> None:
        super().__init__(module_name= "MainEnc")

    def encrypt(self, msg: str) -> str:
        return msg

    def decrypt(self, msg: str) -> str:
        return msg

class UI(module.UI):
    def __init__(self) -> None:
        super().__init__(module_name= "MainUI")
        # self.ui = MessengerUI()
        self.ip = socket.gethostbyname(socket.gethostname())
        self.chats = Chats()                 # init Chats here; no external chat arg
        self.reserve_bottom = 1
        self.poll_interval = 0.05
        self.input_str = ""
        self.running = True

    def send_message(self, msg: str):
        ip = msg.split(":")[0]
        msg = "".join(msg.split(":")[1:])
        if ip == "quit":
            self.stop_ui()
            return
        self.net.send_msg(msg, ip)
        # placeholder: add to chats; override if needed
        self.chats.add_message(msg, sender="You", reciver="Other")

    def add_message(self, message: str, sender: str, reciver: str):
        self.chats.add_message(message, sender, reciver)

    def _draw_messages(self, stdscr, max_y: int, max_x: int, scroll: int):
        stdscr.erase()
        usable_rows = max_y - self.reserve_bottom
        msgs = self.chats.snapshot()
        lines = [f'{m["sender"]}: {m["msg"]}' for m in msgs]
        for idx in range(usable_rows):
            msg_idx = idx + scroll
            if msg_idx < len(lines):
                stdscr.addnstr(idx, 0, lines[msg_idx], max_x - 1)

    def _compute_scroll(self, max_y: int) -> int:
        usable_rows = max_y - self.reserve_bottom
        msgs = self.chats.snapshot()
        return max(0, len(msgs) - usable_rows)

    def _run(self, stdscr):
        curses.curs_set(1)
        stdscr.nodelay(True)
        stdscr.keypad(True)

        while self.running:
            max_y, max_x = stdscr.getmaxyx()
            scroll = self._compute_scroll(max_y)
            self._draw_messages(stdscr, max_y, max_x, scroll)

            prompt = "> "
            input_y = max_y - self.reserve_bottom
            stdscr.move(input_y, 0)
            stdscr.clrtoeol()
            stdscr.addnstr(input_y, 0, prompt + self.input_str, max_x - 1)
            stdscr.move(input_y, len(prompt) + len(self.input_str))
            stdscr.refresh()

            try:
                ch = stdscr.get_wch()
            except curses.error:
                time.sleep(self.poll_interval)
                continue

            if isinstance(ch, str):
                if ch == "\n":
                    msg = self.input_str.strip()
                    if msg:
                        self.send_message(msg)
                    self.input_str = ""
                elif ch == "\x1b":
                    self.running = False
                elif ch in ("\x7f", "\b"):
                    self.input_str = self.input_str[:-1]
                else:
                    self.input_str += ch
            elif isinstance(ch, int):
                if ch == curses.KEY_BACKSPACE:
                    self.input_str = self.input_str[:-1]
                elif ch == curses.KEY_RESIZE:
                    pass

    def run(self):
        # initialize curses screen here and call internal runner
        curses.wrapper(self._run)
    def start_ui(self):
        self.run()

    def stop_ui(self):
        self.running = False
        self.net.stop_server()
    
    def on_message_recive(self, msg: str, sender: str) -> None:
        self.add_message(msg, sender, self.ip)
        print(f"{sender:<10}| {msg}")


class Network(module.Network):
    def __init__(self) -> None:
        super().__init__(module_name= "MainNet")
        self.server_running = True
        addr = ('0.0.0.0', SERVER_PORT)
        self.active_connections = set()

    def init_network(self, encryption: module.Encryption, ui: module.UI) -> None:
        self.enc = encryption
        self.ui = ui
        addr = ('0.0.0.0', SERVER_PORT)
        self.server = Server(addr)
        server_thread = Thread(target= self.start_server)
        server_thread.start()

    def send_msg(self, msg: str, dest: str, msg_type: str= "message") -> None:
        addr = (dest, SERVER_PORT)
        client = Connection(addr)
        formated = {
            "type": msg_type,
            "content": msg
        }

        encrypted = self.enc.encrypt(json.dumps(formated))
        client.send(encrypted)
        client.close()

    def start_server(self) -> None:
        while True:
            msg, conn, addr = self.server.get_next()
            sender_ip = addr[0]
            msg = self.enc.decrypt(msg)
            formated = json.loads(msg)
            match formated["type"]:
                case "message":
                    self.ui.on_message_recive(formated["content"], sender_ip)
                case "join_message":
                    self.active_connections.add(sender_ip)
                    if not hasattr(self.ui, "chats"):
                        continue
                    allowed_messages = self.ui.chats.filter_by_access(sender_ip)
                    self.send_msg(json.dumps(allowed_messages), sender_ip, "chats")
                case "chats":
                    if not hasattr(self.ui, "chats"):
                        continue
                    messages = json.loads(formated["content"])
                    self.ui.chats.update_messages(messages)
                case "quit_message":
                    self.active_connections.remove(sender_ip)
                case "quit":
                    break
            
    def stop_server(self) -> None:
        if self.server_running:
            self.send_msg("", "127.0.0.1", "quit")
            self.server_running = False
            if len(self.active_connections) > 0:
                self.send_msg("", list(self.active_connections)[0], "quit_message")
    

class ConfigParser(module.ConfigParser):
    def __init__(self) -> None:
        super().__init__(module_name= "MainParser")
    def parse(self) -> Config:
        config = Config(
            net= "MainNet",
            ui= "MainUI",
            encryption= "MainEnc",
            application= "MainApp"
        )
        return config
