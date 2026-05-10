from src import module
from src.vars import *
from dataclasses import dataclass
import threading
from threading import Thread
from socket_for_humans import Server, Connection
import json

@dataclass
class Config:
    net: module.Module
    ui: module.Module
    encryption: module.Module
    application: module.Module

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

    def start_ui(self):
        pass
    
    def on_message_recive(self, msg: str, src: str) -> None:
        print(f"{src:<10}| {msg}")

class Network(module.Network):
    def __init__(self) -> None:
        super().__init__(module_name= "MainNet")
        self.server_running = True
        addr = ('0.0.0.0', SERVER_PORT)
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
            src = addr[0]
            msg = self.enc.decrypt(msg)
            formated = json.loads(msg)
            if formated["type"] == "message":
                self.ui.on_message_recive(formated["content"], src)
            elif formated["type"] == "quit":
                break
            
    def stop_server(self) -> None:
        if self.server_running:
            self.send_msg("", "127.0.0.1", "quit")
            self.server_running = False
    

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
