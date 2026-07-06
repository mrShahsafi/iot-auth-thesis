import pandas as pd
import matplotlib.pyplot as plt

from .Hybrid_2_with_new_changes import OUTPUT_FILE

df = pd.read_csv()
plt.figure(figsize=(8, 4))
df.boxplot(column="latency_ms", by="node_id")
plt.ylabel("Latency (ms)")
plt.title("Boxplot Latency per Node")
plt.suptitle("")
plt.show()
