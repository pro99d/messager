from collections.abc import Callable
import logging
from typing import Type
type name = str
import os
from .vars import *

if os.path.exists(LOG_FILE):
    os.rename(LOG_FILE, LOG_FILE + ".old")
logging.basicConfig(
                    filename=LOG_FILE,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO
                    )

logger = logging.Logger("module logger")
class Module:
    def __init__(self, module_name: name= "missing", module_type: str= "missing") -> None:
        self._name: name = module_name
        self._type: str = module_type
        logging.info(f"Module {module_name} initialized successfully.")

    def _get_fields(self) -> list[name]:
        methods = []
        for i in dir(self):
            if not i.startswith("_"):
                methods.append(i)
        return methods

class ModuleManager:
    def __init__(self) -> None:
        self.modules: dict[name, Module] = {}

    def init_module(self, module: Type[Module]) -> None:
        mod = module()
        self.modules[mod._name] = mod

    def get_methods(self, method_name: name) -> list[Callable]:
        methods: list[Callable] = []
        for module in self.modules.values():
            if method_name in module._get_fields():
                methods.append(getattr(module, method_name))
        return methods

    def get_module_by_name(self, module_name: name) -> Module:
        if module_name in self.modules.keys():
            return self.modules[module_name]
        else:
            raise ModuleNotFoundError(f"Module {module_name} is not found. Is it loaded?")
    
    def get_module_by_type(self, module_type: name) -> list[Module]:
        modules: list[Module] = []
        for module in self.modules.values():
            if module.type == module_type:
                modules.append(module)
        return modules

if __name__ == "__main__":
    m = Module("Test")
