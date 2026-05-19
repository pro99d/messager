import threading
import time
from dataclasses import dataclass
from threading import Thread
from typing import List, Dict, Set

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from src import module
from src.vars import *

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

class UI(module.UI, App):
    """A textual messager app"""

    BINDINGS = [("d", "toggle-dark", "Toggle dark mode")]

    def __init__(self) -> None:
        super(module.UI, self).__init__(module_name= "MainUI")

    def init_mod(self, net) -> None:
        super().init_mod(net)
        # self.net.send_msg("", ip in that network, "join_message")

    def start_ui(self):
        self.run()

    def stop_ui(self):
        self.running = False
        self.net.stop_server()

    def compose(self) -> ComposeResult:
        """Create child widgets for ui"""
        yield Header()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""

        self.theme = (
        "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

class StopwatchApp(App):
    """A Textual app to manage stopwatches."""
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

        
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()

        
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
                    
        "textual-dark" if self.theme == "textual-light" else "textual-light"
                
        )
if __name__ == "__main__":
    app = StopwatchApp()
    app.run()
