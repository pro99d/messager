import json
import threading
import time
from dataclasses import dataclass
from threading import Thread
import curses
from typing import List, Dict, Set
import socket
import logging

import textual
import netifaces

from src import module
from src.vars import *



def get_interface_ips():
    interfaces = netifaces.interfaces()
    ips = []
    for interface in interfaces:
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            ips.extend([addr['addr'] for addr in addrs[netifaces.AF_INET]])
        if netifaces.AF_INET6 in addrs:
            ips.extend([addr['addr'] for addr in addrs[netifaces.AF_INET6]])
    for i in ips:
        if i.startswith("192.168"):
            return i

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
        self.ip = get_interface_ips()
        print(self.ip)
        self.chats: Chats = Chats()                 # init Chats here; no external chat arg
        self.reserve_bottom = 1
        self.poll_interval = 0.05
        self.input_str = ""
        self.running = True
    def init_mod(self, net) -> None:
        super().init_mod(net)
        self.net.send_msg("", input("enter ip that in network. "), "join_message")

    def send_message(self, msg: str):
        ip = msg.split(":")[0]
        msg = "".join(msg.split(":")[1:])
        if ip == "quit":
            self.stop_ui()
            return
        self.net.send_msg(msg, ip)
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
        super().__init__(module_name="MainNet")
        self.server_running = True
        self.addr = ('0.0.0.0', SERVER_PORT)
        self.active_connections: Set[str] = set()
        self._ac_lock = threading.Lock()
        self.enc = None
        self.ui = None
        self._server_thread = None

    def init_network(self, encryption: module.Encryption, ui: module.UI) -> None:
        self.enc = encryption
        self.ui = ui
        self.addr = ('0.0.0.0', SERVER_PORT)
        self._server_thread = Thread(target=self.start_server, daemon=True)
        self._server_thread.start()

    def send_msg(self, msg: str, dest: str, msg_type: str = "message", timeout: float = 5.0) -> None:
        addr = (dest, SERVER_PORT)
        try:
            payload = {"type": msg_type, "content": msg}
            # assume enc.encrypt returns a str; convert to bytes for network
            encrypted_bytes = self.enc.encrypt(json.dumps(payload)).encode()
            with socket.create_connection(addr, timeout=timeout) as s:
                s.sendall(encrypted_bytes)
        except Exception as e:
            logging.error(f"Error {e} in send msg in network. destination: {dest}")

    def start_server(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(self.addr)
                s.listen()
                while self.server_running:
                    try:
                        conn, addr = s.accept()
                    except Exception:
                        continue
                    Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
        finally:
            self.server_running = False

    def _handle_client(self, conn: socket.socket, addr):
        with conn:
            try:
                data_chunks = []
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data_chunks.append(chunk)
                raw = b"".join(data_chunks)
                if not raw:
                    return
                # assume decrypt expects str input; decode first
                decrypted = self.enc.decrypt(raw.decode())
                formated = json.loads(decrypted)
                sender_ip = addr[0]
                t = formated.get("type")
                if t == "message":
                    self.ui.on_message_recive(formated.get("content", ""), sender_ip)
                elif t == "join_message":
                    with self._ac_lock:
                        self.active_connections.add(sender_ip)
                    if not hasattr(self.ui, "chats"):
                        return
                    allowed_messages = self.ui.chats.filter_by_access(sender_ip)
                    self.send_msg(json.dumps(allowed_messages), sender_ip, "chats")
                elif t == "chats":
                    if not hasattr(self.ui, "chats"):
                        return
                    messages = json.loads(formated.get("content", "[]"))
                    self.ui.chats.update_messages(messages)
                elif t == "quit_message":
                    with self._ac_lock:
                        self.active_connections.discard(sender_ip)
                elif t == "quit":
                    # request to stop server
                    self.server_running = False
            except Exception:
                pass

    def stop_server(self) -> None:
        if self.server_running:
            # trigger server loop to exit by connecting and sending quit
            try:
                self.send_msg("", "127.0.0.1", "quit")
            except Exception:
                pass
            self.server_running = False
            with self._ac_lock:
                if self.active_connections:
                    try:
                        peer = next(iter(self.active_connections))
                        self.send_msg("", peer, "quit_message")
                    except Exception:
                        pass

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
