from settings import LOG_CSV

CSV_FIELDS = (
    "node_id,k,latency_ms,bytes,battery,energy,wait_ms,enc_ms,transport_ms,dec_ms,match_ms,"
    "genuine,impostor,genuine_accepted,impostor_accepted,hmac_failed,replay,light,decision_ms,decision_bytes,ack_bytes"
).split(",")


def create_output_csv(mode=None):
    with open(LOG_CSV, "w", newline="") as f:
        f.write(",".join(CSV_FIELDS) + "\n")
