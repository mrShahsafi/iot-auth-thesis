from settings import NUM_NODES


def init_energy_consumption(init_value=0.0, num_nodes=None):
    _num_nodes = num_nodes or NUM_NODES
    energy_consumption = {node: init_value for node in range(_num_nodes)}
    return energy_consumption
