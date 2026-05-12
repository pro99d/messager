from . import module
import importlib
import os
import pathlib
from dataclasses import dataclass
import mods
from src.vars import *

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
        
        # modules = module.Module.__subclasses__()
        self.init_submodules(module.Module)
        with open(F"{CONFIG_PATH}/parser", "r") as f:
            parser_name = f.read().strip()

        config_parser = self.module_manager.get_module_by_name(parser_name)
        config = config_parser.parse()
        self.ui = self.module_manager.get_module_by_name(config.ui)
        self.net = self.module_manager.get_module_by_name(config.net)
        self.encryption = self.module_manager.get_module_by_name(config.encryption)
        self.net.init_network(encryption= self.encryption, ui= self.ui) 
        self.ui.init_mod(self.net)
        self.ui.start_ui()

    def start(self) -> None:
        self.net.send_msg("Hi!", '127.0.0.1')

    def init_submodules(self, module: type[module.Module]) -> None:
        modules = module.__subclasses__()
        for load_module in modules:
            self.init_submodules(load_module)
            self.module_manager.init_module(load_module)


def main():
    starter = Starter()
    try:
        starter.start()
    # except Exception as e:
        # print(e)
    finally:
        starter.net.stop_server()
        starter.ui.stop_ui()


if __name__ == "__main__":
    main()
