from src import module
from src import vars
from dataclasses import dataclass

@dataclass
class Config:
    client: module.Module
    server: module.Module
    ui: module.Module
    encryption: module.Module
    application: module.Module

class Application(module.Module):
    def __init__(self) -> None:
        super().__init__(module_name= "MainApp", module_type= "App")

class ConfigParser(module.Module):
    def __init__(self) -> None:
        super().__init__(module_name= "MainParser", module_type="Parser")
    def parse(self) -> Config:
        config = Config(
            client= "MainClient",
            server= "MainServer",
            ui= "MainUI",
            encryption= "MainEnc",
            application= "MainApp"
        )
