import sys
import os
import threading
from collections import defaultdict, deque

from settings import MODE, OUTPUT_FILE, NUM_NODES, LOG_CSV
from .utils import create_output_csv
from .core import tensor_context, init_energy_consumption, generate_biometric_vector


def init_app(dry_run=False):
    """Initialize application components and global variables."""
    # Add root of project to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    context = tensor_context()
    energy_consumption = init_energy_consumption()
    recent_timestamps = defaultdict(lambda: deque(maxlen=100))

    if not dry_run:
        create_output_csv()

    lock = threading.Lock()
    trusted_database = generate_biometric_vector()

    return context, energy_consumption, recent_timestamps, lock, trusted_database
