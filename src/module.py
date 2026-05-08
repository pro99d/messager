type name = str
class Module:
    def __init__(self, name: str) -> None:
        self.name: str = name

    def _get_fields(self) -> list[name]:
        methods = []
        for i in dir(self):
            if not i.startswith("_"):
                methods.append(i)
        return methods

class ModuleManager:
    def __init__(self) -> None:
        self.modules: dict[name, Module] = {}

    def init_module(self, module: Module) -> None:
        self.modules[module.name] = module

    def get_methods(self, method_name: name) -> list[function]:
        methods: list[function] = []
        for module in self.modules.values():
            if method_name in module._get_fields():
                methods.append(getattr(module, method_name))
        return methods

    def get_module(self, module_name: name) -> Module:
        if module_name in self.modules.keys():
            return self.modules[module_name]
        else:
            raise ModuleNotFoundError(f"Module {module_name} is not found. Is it loaded?")

if __name__ == "__main__":
    m = Module("Test")
