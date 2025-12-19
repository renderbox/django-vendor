from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("vendor")
except PackageNotFoundError:
    __version__ = "0.0.0"

VERSION = __version__
