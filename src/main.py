import module
import importlib
import os
import pathlib
from dataclasses import dataclass

MODULE_DIR = pathlib.Path("src/")

@dataclass
class Config:
    client: module.Module
    server: module.Module
    ui: module.Module
    encryption: module.Module
    application: module.Module

class Application(module.Module):
    def __init__(self) -> None:
        super().__init__(module_name= "App", module_type= "Main app")

class Starter:
    def __init__(self):
        self.module_manager = module.ModuleManager()
        modules = module.Module.__subclasses__()
        for load_module in modules:
            self.module_manager.init_module(load_module)
            

def main():
    starter = Starter()
    print("Hello from messanger!")


if __name__ == "__main__":
    main()
