# PacketLab — macOS native edition

**Runs on Apple Silicon and Intel Macs with Python 3.10+. No Ubuntu, UTM, NS2, or NAM required for the default engine.**

## Launch in VS Code

1. Extract the ZIP, then open the `tcp_udp_lab` folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Run `bash setup_mac.sh` once (requires internet to install Python dependencies).
4. Run `bash start_mac.sh`.
5. Visit **http://127.0.0.1:5000** in your browser.
6. Choose **Native Python · macOS ready**, configure all five impairments, and click **Run simulation** or **Run standard experiment suite**.

Stop the server with Ctrl+C.

## Command-line experiments

```bash
source .venv/bin/activate
python3 -m experiments.run
python3 -m analysis.plots
python3 -m unittest discover -s tests -v
```

Results: `results/*.json`, `results/summary.csv`, `results/plots/*.png`. Download a CSV directly from the dashboard.

## What the engines really do

**Native Python (default):** A reproducible educational **discrete-event model**, with two flows sharing a FIFO 1 Mbps bottleneck. UDP sends constant-bit-rate datagrams; the TCP-like sender uses **stop-and-wait automatic repeat request (ARQ)** and retransmission after timeouts. Random loss, delay, checksum rejection of corrupted packets, duplication, and jitter-induced reordering are simulated. It is **not** the operating system's TCP stack, **not TCP Reno**, and **not a measurement of real socket performance**. Reordering and duplication are tracked; a receiver discards duplicate packets. TCP acknowledgments are abstracted and assumed reliable. The model's queue occupancy and integrity measures are approximations.

**NS2 (optional):** Original Tcl scenario for TCP Reno / FTP and UDP / CBR, loss, delay and queue size. Needs `ns` executable installed separately; NS2 generates `.tr` and `.nam` files. Other impairments are not available in the NS2 backend. The NS2 backend is retained for an optional extra credit demonstration.

**Socket demonstration:** `python3 -m socket_lab.impairment_demo` runs a separate localhost UDP demonstration, independent of the dashboard model.

### Important for your report

Label native graphs **“educational discrete-event simulation of TCP-like ARQ vs UDP”**. Do not call them actual TCP Reno results, real packet captures, or Wireshark measurements. To measure real TCP vs UDP behavior, an additional real-socket test harness and impairment mechanism are required. NAM is optional and not needed to run the macOS version.

## Files

- `experiments/native.py` — native simulator
- `experiments/run.py` — batch experiment runner, optional NS2 backend
- `web/app.py` — Flask JSON API and dashboard server
- `web/templates/index.html`, `web/static/` — dashboard UI/UX
- `analysis/plots.py` — graph generation
- `ns2/tcp_udp.tcl` — optional NS2 scenario
- `socket_lab/impairment_demo.py` — localhost UDP impairment demo


## v2 dashboard fix (October 2026)
- Fixed missing `modelLabel` element that caused `null is not an object` when running simulations.
- Added a cache-busting JavaScript URL so Safari loads the updated code.
- Added graceful handling for malformed metrics in the chart renderer.
- If replacing a running project, stop the old server with Ctrl+C, run `bash start_mac.sh` from this new folder, then hard-refresh the browser (Cmd+Shift+R).
