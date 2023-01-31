import importlib.metadata

try:
    __version__ = importlib.metadata.version("vendor")
    print("DIR NAME")
    print(os.path.dirname(__file__))
except:     # This is to support installing the package locally via "pip install -e ." where a metadata files is not yet been created.
    import toml, os
    module_dir = os.path.dirname(__file__)
    cfg = toml.load(module_dir + "/../../pyproject.toml")
    __version__ = cfg['project']['version']

VERSION = __version__
