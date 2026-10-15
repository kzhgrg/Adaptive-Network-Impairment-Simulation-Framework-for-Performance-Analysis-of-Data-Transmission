"""Parser for NS2's classic wired trace format.

Classic lines: event time from to type size flags fid src dst seq uid
Counts source enqueue (+) as offered packets, destination receive (r) as
successfully delivered packets. UDP PDR uses unique IDs. TCP PDR is
reported as a *transmission delivery ratio*, not application reliability;
TCP sequence repeats are a retransmission estimate, not an exact counter.
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path

FLOW = {"tcp": 1, "udp": 2}
SOURCE = {"tcp": "0", "udp": "1"}
DESTINATION = {"tcp": "4", "udp": "5"}
DURATION = 11.0  # traffic active from t=1 to t=12


def parse_trace(path: str | Path) -> dict:
    sent = defaultdict(dict)
    received = defaultdict(dict)
    dropped = defaultdict(set)
    sent_seq = defaultdict(list)
    recv_bytes = defaultdict(int)
    events = defaultdict(list)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.split()
            if len(p) < 12 or p[0] not in ("+", "-", "r", "d"):
                continue
            event, time, src, dst, ptype, size, flags, fid, address_src, address_dst, seq, uid = p[:12]
            if fid not in ("1", "2") or ptype == "ack":
                continue
            flow = "tcp" if fid == "1" else "udp"
            try:
                t, byte_count = float(time), int(size)
            except ValueError:
                continue
            if event == "+" and src == SOURCE[flow]:
                sent[flow].setdefault(uid, (t, byte_count))
                if flow == "tcp":
                    sent_seq[flow].append(seq)
            if event == "r" and dst == DESTINATION[flow]:
                if uid not in received[flow]:
                    received[flow][uid] = (t, byte_count)
                    recv_bytes[flow] += byte_count
                    events[flow].append((t, byte_count))
            if event == "d":
                dropped[flow].add(uid)
    result = {}
    for flow in ("tcp", "udp"):
        s, r = sent[flow], received[flow]
        n_sent, n_recv = len(s), len(r)
        delays = [r[uid][0] - s[uid][0] for uid in r if uid in s]
        retrans = (len(sent_seq[flow]) - len(set(sent_seq[flow]))) if flow == "tcp" else 0
        result[flow] = {
            "sent_packets": n_sent,
            "received_packets": n_recv,
            "delivery_ratio_percent": round(100 * n_recv / n_sent, 2) if n_sent else 0,
            "unreceived_packets": max(0, n_sent - n_recv),
            "trace_drop_events": len(dropped[flow]),
            "throughput_kbps": round(recv_bytes[flow] * 8 / DURATION / 1000, 2),
            "average_delay_ms": round(sum(delays) / len(delays) * 1000, 3) if delays else None,
            "retransmission_estimate": retrans,
            "received_bytes_including_headers": recv_bytes[flow],
        }
    return result


def save_metrics(metrics: dict, output: str | Path) -> None:
    Path(output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def write_summary(rows: list[dict], output: str | Path) -> None:
    columns = ["scenario", "loss_percent", "delay_ms", "queue_packets", "seed", "engine", "corruption_percent", "duplication_percent", "reordering_percent", "flow", "sent_packets", "received_packets", "delivery_ratio_percent", "unreceived_packets", "trace_drop_events", "throughput_kbps", "average_delay_ms", "retransmission_estimate", "corrupted_packets", "duplicate_packets", "reordered_packets", "integrity_percent"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
