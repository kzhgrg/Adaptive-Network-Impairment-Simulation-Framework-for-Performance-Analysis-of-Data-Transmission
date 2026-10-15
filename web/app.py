"""Local research dashboard. Bind to loopback; not a public production service."""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template, request, Response
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.run import run_one, run_all, RESULTS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10_000


def existing_results():
    if not RESULTS.exists():
        return []
    records = []
    for path in RESULTS.glob("*.json"):
        if path.name == "summary.json" or path.name.endswith(".events.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "metrics" in data:
                records.append(data)
        except (ValueError, OSError):
            continue
    return sorted(records, key=lambda item: item.get("scenario", ""))


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/results")
def results():
    return jsonify(existing_results())


@app.post("/api/run")
def run():
    body = request.get_json(silent=True) or {}
    try:
        loss = float(body.get("loss", 0))
        delay = float(body.get("delay", 10))
        queue = int(body.get("queue", 20))
        seed = int(body.get("seed", 7))
        corruption = float(body.get("corruption", 0))
        duplication = float(body.get("duplication", 0))
        reordering = float(body.get("reordering", 0))
        engine = body.get("engine", "native")
        if not (0 <= loss <= 100 and 0 <= delay <= 2000 and 1 <= queue <= 10000 and 0 <= seed <= 1000000 and all(0 <= v <= 100 for v in (corruption, duplication, reordering)) and engine in ("native", "real", "ns2")):
            raise ValueError("Parameters are outside allowed ranges")
        # Use controlled numeric parameters only; no arbitrary shell commands.
        name = f"{engine}_l{loss:g}_d{delay:g}_q{queue}_c{corruption:g}_u{duplication:g}_r{reordering:g}_s{seed}".replace(".", "p")
        return jsonify(run_one(name, loss, delay, queue, seed, corruption, duplication, reordering, engine))
    except (ValueError, RuntimeError, TimeoutError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Simulation failed")
        return jsonify({"error": f"Simulation failed: {type(exc).__name__}"}), 500


@app.post("/api/run-all")
def run_batch():
    try:
        return jsonify(run_all(engine=(request.get_json(silent=True) or {}).get("engine", "native")))
    except Exception as exc:
        app.logger.exception("Batch failed")
        return jsonify({"error": f"Batch failed: {exc}"}), 500


@app.get("/api/export.csv")
def export():
    buffer = io.StringIO()
    fields = ["scenario", "loss_percent", "delay_ms", "queue_packets", "seed", "engine", "corruption_percent", "duplication_percent", "reordering_percent", "flow", "sent_packets", "received_packets", "delivery_ratio_percent", "unreceived_packets", "trace_drop_events", "throughput_kbps", "average_delay_ms", "retransmission_estimate", "corrupted_packets", "duplicate_packets", "reordered_packets", "integrity_percent"]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for entry in existing_results():
        for flow, metrics in entry["metrics"].items():
            writer.writerow({**{k: entry.get(k) for k in fields}, "flow": flow, **metrics})
    return Response(buffer.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=tcp_udp_results.csv"})




@app.get("/api/events/<scenario>")
def event_trace(scenario):
    if not scenario.replace('_','').replace('-','').isalnum() or len(scenario)>60:
        return jsonify({"error": "Invalid scenario"}), 400
    path = RESULTS / (scenario + ".events.json")
    if not path.is_file():
        return jsonify({"error": "No event trace for this experiment"}), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8")))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
