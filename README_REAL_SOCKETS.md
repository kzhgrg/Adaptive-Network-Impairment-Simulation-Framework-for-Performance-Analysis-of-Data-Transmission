# PacketLab: Real TCP and UDP sockets on macOS and Windows

This edition preserves the original Flask dashboard and educational simulator and adds a **Real TCP + UDP sockets** engine in the Simulation Lab dropdown.

## Start on Mac

```bash
bash setup_mac.sh     # once
bash start_mac.sh     # each time
```

Open `http://127.0.0.1:5000`, choose **REAL TCP + UDP sockets**, adjust sliders, and click **Run simulation**. (The button name is inherited; this engine actually opens local TCP and UDP sockets.)

## Start on Windows (PowerShell)

```powershell
.\setup_windows.bat
.\start_windows.bat
```

## What is measured

- Actual `socket.SOCK_STREAM` TCP and `socket.SOCK_DGRAM` UDP connections on loopback (`127.0.0.1`), with 36 deterministic 512-byte payloads per flow.
- An **application-level relay scheduler** that can omit, delay, corrupt, duplicate, and reorder *application messages* before sending them through sockets.
- Per-sequence SHA-256 payload integrity verification, delivered unique messages, duplicates, corruption, out-of-order arrivals, elapsed time and delivered-payload throughput.
- Per-experiment `results/<scenario>.json` and `results/<scenario>.events.json` with timestamped relay/receive events; CSV export through the dashboard.
- Existing native simulator and optional NS2 backend remain available.

## IMPORTANT: what this does *not* prove

- **This is NOT real IP packet loss or TCP segment loss**. A dropped relay message is never written into a TCP socket, so the TCP kernel cannot retransmit it. TCP's actual reliable delivery operates *within each socket connection*. For real TCP congestion control, retransmissions and kernel-level impairments, use a separate Linux `tc netem` or network emulator experiment with real TCP sockets.
- The app-level `queue` is a simple relay scheduling cap, not a router queue; `retransmission_estimate=0` means not measured, not proof that the kernel never retransmitted.
- Experiments are localhost measurements, not WAN benchmarks. TCP and UDP timings are not directly comparable as pure protocol overhead because this relay and UDP receive-drain differ. No Wireshark capture integration is included.
- `average_delay_ms` measures elapsed time since the flow started until receipt, not a per-packet network one-way delay.
- Do not call this a faithful TCP Reno vs UDP packet-loss comparison in your report.

## Testing

```bash
python -m unittest discover -s tests -v
python -m socket_lab.real_experiment
```

## GitHub

Commit the **extracted project folder**, not the ZIP itself. `.gitignore` excludes `.venv/`, Python caches and generated result files.
