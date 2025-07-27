from .base import *
try:
    from .local import *
except ImportError:
    pass
print(f"You are in the {MODE} mode")
print(f"DIR: {BASE_DIR}")
