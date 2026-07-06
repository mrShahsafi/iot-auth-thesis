from settings import MODE, LOG_CSV


def create_output_csv(mode=None):
    _mode = mode or MODE
    _file = LOG_CSV
    with open(_file, "w", newline="") as f:
        f.write("node_id,latency_ms,bytes,battery,energy\n")
