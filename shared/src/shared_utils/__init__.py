"""
shared_utils: tiny helpers reused across scripts.
"""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("shared-utils")
except PackageNotFoundError:  # editable/uninstalled dev fallback
    __version__ = "0.0.0.dev"

# Top-level helpers
from .json_read import load_json
from .chart_transplant import transplant_charts

__all__ = ["load_json", "transplant_charts", "__version__"]