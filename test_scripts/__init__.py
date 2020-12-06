import os

__all__ = ['test_suite']

test_modules = [file[:len(file)-3] for file in os.listdir(os.path.abspath(__path__[0])) if file.startswith('test_')]
this    = [__import__('test_scripts.' + name) for name in test_modules][0]
ModuleType = type(os)

test_suite = []

for attribName in [module for module in dir(this) if module.startswith('test_')]:
    parent, obj = this, getattr(this,attribName)
    if isinstance(obj,ModuleType):
        test_suite.append(obj)


