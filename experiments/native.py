"""Reproducible educational discrete-event TCP-like ARQ vs UDP simulation.

Not a kernel TCP stack or an NS2 result. Shared FIFO bottleneck, Bernoulli loss,
corruption, duplication, and jitter-induced reordering. TCP-like reliable delivery
uses a stop-and-wait ARQ model, not TCP Reno congestion control.
"""
from __future__ import annotations
import heapq
import random
from dataclasses import dataclass

PACKET_BYTES = 1000
DURATION = 10.0
LINK_BPS = 1_000_000

@dataclass
class Stats:
    sent_packets: int = 0
    received_packets: int = 0
    unreceived_packets: int = 0
    trace_drop_events: int = 0
    throughput_kbps: float = 0.0
    average_delay_ms: float = 0.0
    retransmission_estimate: int = 0
    corrupted_packets: int = 0
    duplicate_packets: int = 0
    reordered_packets: int = 0
    integrity_percent: float = 100.0


def simulate(loss=0, delay=10, queue=20, seed=7, corruption=0, duplication=0, reordering=0):
    """Return two-flow measurements. Probabilities are percentages.

    TCP-like traffic is stop-and-wait ARQ with timeout/retry and acknowledgments
    abstracted as reliable; UDP sends CBR at 100 pps. Both share a forward FIFO
    1 Mbps link. Jitter affects arrival ordering but not bottleneck service order.
    """
    for name, val in [('loss',loss),('corruption',corruption),('duplication',duplication),('reordering',reordering)]:
        if not 0 <= val <= 100: raise ValueError(f'{name} must be 0–100%')
    if not 0 <= delay <= 2000 or not 1 <= queue <= 10000 or not 0 <= seed <= 1_000_000:
        raise ValueError('Invalid delay, queue, or seed')
    rng = random.Random(seed)
    # Event heap: time, counter, event kind, protocol, sequence, generation.
    events = []
    order = 0
    def schedule(t, kind, flow, seq, gen=0):
        nonlocal order
        order += 1
        heapq.heappush(events, (t, order, kind, flow, seq, gen))
    udp_count = int(DURATION * 100)
    for i in range(udp_count): schedule(i * 0.01, 'send', 'udp', i)
    schedule(0.0, 'send', 'tcp', 0)
    # FIFO shared queue. Link service takes 8 ms per 1000-byte packet.
    next_free = 0.0
    outstanding = {}
    first_sent = {'tcp':{}, 'udp':{}}
    delivered = {'tcp':set(), 'udp':set()}
    received_order = {'tcp':[], 'udp':[]}
    arrivals = {'tcp':[], 'udp':[]}
    counters = {f: {'attempts':0,'drops':0,'corrupt':0,'duplicates':0,'retries':0} for f in ('tcp','udp')}
    tcp_next = 0
    tcp_limit = 500
    timeout = max(.15, 4*(delay/1000 + .008))
    while events:
        t, _, kind, flow, seq, gen = heapq.heappop(events)
        if kind == 'send':
            if t > DURATION: continue
            if flow == 'tcp' and (seq != tcp_next or seq in delivered['tcp']): continue
            c = counters[flow]
            c['attempts'] += 1
            if gen: c['retries'] += 1
            first_sent[flow].setdefault(seq,t)
            # DropTail occupancy approximation: queued transmissions still waiting.
            waiting = max(0, int((next_free-t)/(.008) + 1e-9))
            if waiting >= queue:
                c['drops'] += 1
            else:
                finish = max(t, next_free) + .008
                next_free = finish
                if rng.random() < loss/100:
                    c['drops'] += 1
                else:
                    bad = rng.random() < corruption/100
                    if bad: c['corrupt'] += 1
                    # A delayed packet may be overtaken by later packets.
                    extra = rng.uniform(.02,.15) if rng.random() < reordering/100 else 0
                    arrival = finish + delay/1000 + extra
                    schedule(arrival, 'arrive', flow, seq, int(bad))
                    if rng.random() < duplication/100:
                        c['duplicates'] += 1
                        schedule(arrival + rng.uniform(.0001,.02), 'arrive', flow, seq, int(bad))
            if flow == 'tcp':
                schedule(t + timeout, 'timeout', flow, seq, gen + 1)
        elif kind == 'arrive':
            if gen: continue  # failed checksum
            if seq in delivered[flow]: continue  # duplicate ignored by receiver
            delivered[flow].add(seq)
            received_order[flow].append(seq)
            arrivals[flow].append(max(0, t-first_sent[flow][seq]))
            if flow == 'tcp' and seq == tcp_next:
                tcp_next += 1
                if tcp_next < tcp_limit and t < DURATION:
                    schedule(t + .001, 'send', 'tcp', tcp_next)
        elif kind == 'timeout':
            if seq in delivered['tcp'] or seq != tcp_next or t >= DURATION: continue
            schedule(t, 'send', 'tcp', seq, gen)
    out = {}
    for flow in ('tcp','udp'):
        c = counters[flow]
        unique_sent = len(first_sent[flow])
        unique_recv = len(delivered[flow])
        ordered = received_order[flow]
        reordered = sum(ordered[i] < max(ordered[:i]) for i in range(1,len(ordered))) if ordered else 0
        # Effective observation interval includes network propagation tail.
        observation = DURATION + delay/1000 + .2
        out[flow] = dict(
            sent_packets=unique_sent, received_packets=unique_recv,
            delivery_ratio_percent=round(100*unique_recv/unique_sent,2) if unique_sent else 0,
            unreceived_packets=max(0,unique_sent-unique_recv),
            trace_drop_events=c['drops'],
            throughput_kbps=round(unique_recv*PACKET_BYTES*8/observation/1000,2),
            average_delay_ms=round(1000*sum(arrivals[flow])/len(arrivals[flow]),2) if arrivals[flow] else 0,
            retransmission_estimate=c['retries'],
            corrupted_packets=c['corrupt'],duplicate_packets=c['duplicates'],
            reordered_packets=reordered,
            integrity_percent=100.0 if unique_recv else 0.0,
        )
    return out
