"""Real loopback TCP/UDP sockets with a controlled application-layer relay.

This is a *real socket* experiment, not kernel-level packet impairment. UDP
impairments affect datagrams; TCP relay uses framed application records. The
TCP kernel still supplies stream reliability on each loopback TCP connection.
"""
from __future__ import annotations
import hashlib
import json
import random
import socket
import struct
import threading
import time
from dataclasses import dataclass, field

PAYLOAD_BYTES = 512
PACKETS = 36
HEADER = struct.Struct('!I')


def frame(obj):
    data = json.dumps(obj, separators=(',', ':')).encode()
    return HEADER.pack(len(data)) + data


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise EOFError('Connection closed')
        data.extend(part)
    return bytes(data)


def read_frame(sock):
    size = HEADER.unpack(read_exact(sock, 4))[0]
    if size > 100_000:
        raise ValueError('Frame too large')
    return json.loads(read_exact(sock, size))


def packet(i):
    content = bytes((i * 19 + j * 7) % 256 for j in range(PAYLOAD_BYTES))
    return {'seq': i, 'payload': content.hex(), 'sha256': hashlib.sha256(content).hexdigest()}


def corrupt(obj):
    obj = dict(obj)
    s = obj['payload']
    obj['payload'] = ('00' if s[:2] != '00' else 'ff') + s[2:]
    return obj


def validate(obj):
    try:
        return hashlib.sha256(bytes.fromhex(obj['payload'])).hexdigest() == obj['sha256']
    except (ValueError, KeyError):
        return False


@dataclass
class Stats:
    received: dict = field(default_factory=dict)
    duplicates: int = 0
    corrupt: int = 0
    reordered: int = 0
    events: list = field(default_factory=list)
    last_seq: int = -1
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, obj, flow, t0):
        seq = int(obj['seq'])
        valid = validate(obj)
        with self.lock:
            if seq in self.received:
                self.duplicates += 1
                event = 'duplicate'
            elif not valid:
                self.corrupt += 1
                event = 'corrupt'
            else:
                self.received[seq] = (time.monotonic() - t0) * 1000
                event = 'received'
            if seq < self.last_seq:
                self.reordered += 1
            self.last_seq = seq
            self.events.append({'protocol': flow, 'seq': seq, 'event': event, 'time_ms': round((time.monotonic()-t0)*1000, 3)})


def run_flow(flow, loss, delay, queue, seed, corruption, duplication, reordering, count=PACKETS):
    rng = random.Random(seed + (100 if flow == 'tcp' else 200))
    stats = Stats()
    events = []
    start = time.monotonic()
    errors = []
    ready = threading.Event()
    # Receiver is a real TCP or UDP server bound to an ephemeral loopback port.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM if flow == 'tcp' else socket.SOCK_DGRAM)
    listener.bind(('127.0.0.1', 0))
    listener.settimeout(5)
    if flow == 'tcp':
        listener.listen(1)
    receiver_port = listener.getsockname()[1]

    def receiver():
        try:
            if flow == 'tcp':
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(5)
                    while True:
                        try: obj = read_frame(conn)
                        except EOFError: break
                        stats.record(obj, flow, start)
            else:
                listener.settimeout(0.35)
                while not ready.is_set():
                    try: data, _ = listener.recvfrom(8192)
                    except socket.timeout: continue
                    stats.record(json.loads(data), flow, start)
                # drain delayed datagrams
                end = time.monotonic() + 0.2
                while time.monotonic() < end:
                    try: data, _ = listener.recvfrom(8192)
                    except socket.timeout: break
                    stats.record(json.loads(data), flow, start)
        except Exception as exc:
            errors.append(str(exc))
        finally:
            listener.close()

    worker = threading.Thread(target=receiver, daemon=True)
    worker.start()
    sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM if flow == 'tcp' else socket.SOCK_DGRAM)
    sender.settimeout(5)
    if flow == 'tcp': sender.connect(('127.0.0.1', receiver_port))
    # This scheduler emulates application relay behavior, not IP/TCP segment loss.
    pending = []
    for i in range(count):
        obj = packet(i)
        if rng.random() < loss / 100:
            events.append({'protocol': flow, 'seq': i, 'event': 'relay_drop', 'time_ms': round((time.monotonic()-start)*1000, 3)})
            continue
        if rng.random() < corruption / 100:
            obj = corrupt(obj)
            events.append({'protocol': flow, 'seq': i, 'event': 'relay_corrupt', 'time_ms': round((time.monotonic()-start)*1000, 3)})
        copies = 2 if rng.random() < duplication / 100 else 1
        for c in range(copies):
            # jitter creates reorder opportunities for UDP. TCP framing remains ordered once written.
            jitter = rng.uniform(0, max(1, delay * 2)) if rng.random() < reordering / 100 else 0
            pending.append((time.monotonic() + (delay + jitter) / 1000, i, obj))
    pending.sort(key=lambda x: x[0])
    # queue parameter represents a simple relay backlog cap (not OS socket queue).
    # Overflow removes newest scheduled application records.
    if len(pending) > queue * 8:
        for _, seq, _ in pending[queue*8:]:
            events.append({'protocol': flow, 'seq': seq, 'event': 'relay_queue_drop', 'time_ms': round((time.monotonic()-start)*1000, 3)})
        pending = pending[:queue*8]
    try:
        for due, seq, obj in pending:
            wait = due - time.monotonic()
            if wait > 0: time.sleep(wait)
            if flow == 'tcp': sender.sendall(frame(obj))
            else: sender.sendto(json.dumps(obj).encode(), ('127.0.0.1', receiver_port))
            events.append({'protocol': flow, 'seq': seq, 'event': 'relay_forward', 'time_ms': round((time.monotonic()-start)*1000, 3)})
    finally:
        sender.close()
        ready.set()
    worker.join(timeout=6)
    if worker.is_alive(): raise RuntimeError(f'{flow} receiver did not finish')
    if errors: raise RuntimeError(f'{flow} receiver error: {errors[0]}')
    # Exclude the UDP receiver's post-send drain timeout from throughput.
    duration = max(0.001, max((e['time_ms'] for e in events if e['event']=='relay_forward'), default=0) / 1000)
    delivered = len(stats.received)
    avg = sum(stats.received.values()) / delivered if delivered else 0
    metrics = {
        'sent_packets': count, 'received_packets': delivered,
        'delivery_ratio_percent': round(delivered/count*100, 2),
        'unreceived_packets': count-delivered,
        'trace_drop_events': sum('drop' in e['event'] for e in events),
        'throughput_kbps': round(delivered * PAYLOAD_BYTES * 8 / duration / 1000, 2),
        'average_delay_ms': round(avg, 2),
        'retransmission_estimate': 0,
        'corrupted_packets': stats.corrupt,
        'duplicate_packets': stats.duplicates,
        'reordered_packets': stats.reordered,
        'integrity_percent': round(delivered / max(1, delivered+stats.corrupt)*100, 2),
        'duration_seconds': round(duration, 3),
    }
    return metrics, events + stats.events


def run_real(loss, delay, queue, seed=7, corruption=0, duplication=0, reordering=0):
    metrics = {}
    events = []
    for flow in ('tcp', 'udp'):
        metrics[flow], flow_events = run_flow(flow, loss, delay, queue, seed, corruption, duplication, reordering)
        events.extend(flow_events)
    return metrics, events

if __name__ == '__main__':
    print(json.dumps(run_real(5, 20, 20)[0], indent=2))
