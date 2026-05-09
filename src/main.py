from . import module
import importlib
import os
import pathlib
from dataclasses import dataclass
import mods
from .vars import *

def format_path(path: pathlib.Path) -> str:
    strpath = str(path)
    for let in ["/", "\\"]:
        strpath = strpath.replace(let, ".")
    if strpath.endswith(".py"):
        strpath = strpath[:-3]
    return strpath



class Starter:
    def __init__(self):
        self.module_manager = module.ModuleManager()
        if not os.path.isdir(MODULE_DIR):
            os.mkdir(MODULE_DIR)
        # for name in os.listdir(MODULE_DIR):
        #     module_path = format_path(MODULE_DIR / name)
        #     print(module_path)
        #     importlib.import_module(module_path, "../")
        
        modules = module.Module.__subclasses__()
        for load_module in modules:
            self.module_manager.init_module(load_module)
        with open(F"{CONFIG_PATH}/parser", "r") as f:
            parser_name = f.read().strip()

        config_parser = self.module_manager.get_module_by_name(parser_name)
            

def main():
    starter = Starter()

if __name__ == "__main__":
    main()
