# PacketLab — TCP vs UDP Network Performance Observatory

A complete research-project starter implementation with a responsive Flask UI, NS2 network simulation, trace analysis, batch experiments, chart exports, and a separate Python socket impairment demonstration.

## What is included

| Feature | Implementation | Notes |
|---|---|---|
| NS2 topology | `ns2/tcp_udp.tcl` | 6 nodes, shared 1 Mbps bottleneck, DropTail queue |
| TCP/UDP | TCP Reno + FTP, UDP + CBR | Both compete on the bottleneck |
| Packet loss | NS2 ErrorModel | Forward bottleneck link only |
| Delay | NS2 configurable propagation delay | Bottleneck only |
| Congestion | Queue size + shared capacity | DropTail overflow |
| Trace & NAM output | `.tr`, `.nam` | NAM viewer is optional; traces work without it |
| Metrics | `analysis/trace.py` | Delivered throughput, PDR, delay, drop events, retransmission estimate |
| Experiments | `experiments/run.py` | 7 reproducible scenarios |
| Graphs | `analysis/plots.py` | Four PNG comparisons |
| Web UI | `web/app.py`, `web/templates`, `web/static` | Custom responsive dashboard, experiment form, CSV export |
| Corruption/duplication/reordering | `socket_lab/impairment_demo.py` | UDP datagram relay, application-layer impairments |
| TCP socket demo | `socket_lab/impairment_demo.py` | Reliable framed message delivery on localhost |

**Scope note:** The NS2 experiments directly compare TCP and UDP under loss, delay, and congestion. The socket relay demonstrates UDP corruption, duplication, and reordering at the *application datagram* level. It does **not** simulate raw IP packet corruption or subject TCP to the same socket-level impairment model. Do not present these as a fully equivalent apples-to-apples TCP/UDP impairment experiment. TCP retransmission counts are estimates, and trace throughput counts packet bytes including headers. NAM animation files are produced but the NAM GUI is not required.

## Ubuntu 24.04 setup (UTM virtual machine)

```bash
sudo apt update
sudo apt install -y ns2 python3 python3-venv python3-pip
cd ~/TCP_UDP_Project/tcp_udp_lab  # change to where you extracted the zip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Run a single NS2 simulation**

```bash
python3 -m experiments.run --one my_test 2 20 20
```

Arguments are `NAME LOSS_PERCENT DELAY_MS QUEUE_PACKETS`. Trace, NAM, and JSON files appear in `results/`.

**Run all 7 experiments and generate plots**

```bash
python3 -m experiments.run
python3 -m analysis.plots
```

The first command writes `results/summary.csv` and `results/summary.json`. The second writes four images to `results/plots/`.

**Launch the UI**

```bash
python3 -m web.app
```

Open **http://127.0.0.1:5000** in Ubuntu's browser. Use **Run simulation** or **Run standard experiment suite**, inspect metrics, and export CSV. If accessing from the Mac host, configure UTM port forwarding or open the UI within Ubuntu; the server intentionally listens only on localhost.

**Run the Python socket demonstration**

```bash
python3 -m socket_lab.impairment_demo --count 100 --loss 0.05 --delay-ms 2 --corruption 0.03 --duplication 0.05 --reorder 0.1
```

Socket demonstration results are saved as `results/socket_demo.json`. All endpoints use `127.0.0.1` and fixed ports 24561–24563. The relay is intended for one local run at a time.

**Run the unit test**

```bash
python3 -m unittest discover -s tests -v
```

## Network topology

```text
TCP source (0) --\                        /-- TCP destination (4)
                 Router 1 (2) -- Router 2 (3)
UDP source (1) --/       1 Mbps bottleneck \-- UDP destination (5)
```

Source-to-router and router-to-destination links are 10 Mbps with 5 ms propagation. The bottleneck has user-configurable delay and DropTail queue capacity. TCP uses flow ID 1; UDP uses flow ID 2. Data traffic runs from 1s to 12s; the simulation stops at 14s to allow packets to drain.

## Measurement definitions and caveats

- **Throughput**: total destination-received trace packet bytes × 8 / 11 seconds / 1000 (kbps). This includes NS2 packet headers, so it is not pure application goodput.
- **Delivery ratio**: unique received trace packet IDs / unique source-enqueued packet IDs. For TCP this is a transmission-level measure, not an end-to-end application reliability measure. ACKs are excluded.
- **Delay**: mean time between source enqueue and destination receive for matching packet UIDs. One-way network delay, not TCP RTT.
- **Unreceived packets**: source packet IDs not seen at the destination by simulation end; can include in-flight packets, not only drops.
- **Drop events**: distinct packet IDs with a `d` event anywhere in the network; can include retransmissions.
- **Retransmission estimate**: repeated TCP sequence IDs at the source. This is not a guaranteed exact count.
- **Fairness**: TCP FTP is greedy while UDP CBR sends at a fixed rate; the protocols have different offered loads. The comparison reflects competition and response to impairments, not intrinsic protocol superiority.
- **Statistics**: run multiple seeds and compute mean and standard deviation before making scientific claims.

## Project map

```text
analysis/       trace parser and plotting
experiments/    reproducible NS2 experiment runner
ns2/            NS2 Tcl simulation
socket_lab/     Python TCP and UDP socket demonstration
web/            Flask API and responsive UI
results/        generated files
 tests/         parser unit tests
```

## Troubleshooting

- `ns: command not found`: `sudo apt install ns2`.
- `ModuleNotFoundError: flask`: activate `.venv` and run `pip install -r requirements.txt`.
- NAM window doesn't open: **ignore NAM**; `.nam` output is still generated and analysis works from `.tr`.
- If a scenario errors, inspect the error shown by `python3 -m experiments.run --one ...`.
- The dashboard uses Google Fonts when online; system fonts are used offline. Charts themselves need no external JavaScript library.
