from src import module
from src.vars import *
from dataclasses import dataclass
import threading
from threading import Thread
from socket_for_humans import Server, Connection
import json
import time

@dataclass
class Config:
    net: module.Module
    ui: module.Module
    encryption: module.Module
    application: module.Module

class Chats:
    """
    сюда БДшку
    """
    def __init__(self) -> None:
        self.messages = []

    def add_message(self, message: str, sender: str, reciver: str):
        self.messages.append({
            "sender": sender,
            "reciver": reciver,
            "msg": message,
            "time": time.time()
        })

    def update_messages(self, messages: list[dict]) -> None:
        self.messages = list(set(self.messages) | set(messages))

    def filter_by_access(self, ip: str) -> list[dict]:
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
        self.chats = Chats()

    def start_ui(self):
        pass
    
    def on_message_recive(self, msg: str, src: str) -> None:
        print(f"{src:<10}| {msg}")

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
            # if formated["type"] == "message":
            # elif formated["type"] == "quit":
            #     break
            # elif formated["type"]
            
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
