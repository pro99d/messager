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
