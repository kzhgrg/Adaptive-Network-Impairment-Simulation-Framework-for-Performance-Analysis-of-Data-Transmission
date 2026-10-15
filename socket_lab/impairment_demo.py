"""Localhost socket experiment: TCP framing and UDP impairment relay.

UDP impairments are application-level datagram manipulations, not a kernel
network emulator. TCP uses an unmodified direct connection as a reliability
baseline; NS2 experiments are used to study TCP under link loss/congestion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import socket
import struct
import threading
import time
from pathlib import Path

HOST='127.0.0.1'
DEST_PORT=24561
RELAY_PORT=24562
TCP_PORT=24563
PAYLOAD_SIZE=400


def message(seq: int) -> bytes:
    data = (f'packet-{seq:05d}-'.encode() * 40)[:PAYLOAD_SIZE]
    return struct.pack('!I',seq)+hashlib.sha256(data).digest()[:8]+data


def valid(packet: bytes) -> bool:
    return len(packet)>=12 and hashlib.sha256(packet[12:]).digest()[:8]==packet[4:12]


def udp_demo(count: int, loss: float, delay_ms: float, corruption: float, duplication: float, reorder: float, seed: int) -> dict:
    rng=random.Random(seed)
    received=[]
    stop=threading.Event()
    relay_done=threading.Event()

    def receiver():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.bind((HOST,DEST_PORT)); sock.settimeout(.2)
            while not stop.is_set():
                try:
                    packet,_=sock.recvfrom(65535)
                    received.append((struct.unpack('!I',packet[:4])[0],valid(packet),time.monotonic()))
                except socket.timeout:
                    continue

    def relay():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.bind((HOST,RELAY_PORT));sock.settimeout(.3)
            pending=None
            processed=0
            while processed<count:
                try:packet,_=sock.recvfrom(65535)
                except socket.timeout:continue
                processed+=1
                if rng.random()<loss:continue
                if rng.random()<corruption:
                    corrupted=bytearray(packet);corrupted[-1]^=0x01;packet=bytes(corrupted)
                if delay_ms:time.sleep(delay_ms/1000)
                if rng.random()<reorder and pending is None:
                    pending=packet
                    continue
                sock.sendto(packet,(HOST,DEST_PORT))
                if rng.random()<duplication:sock.sendto(packet,(HOST,DEST_PORT))
                if pending is not None:
                    sock.sendto(pending,(HOST,DEST_PORT));pending=None
            if pending is not None:sock.sendto(pending,(HOST,DEST_PORT))
            relay_done.set()

    threads=[threading.Thread(target=receiver,daemon=True),threading.Thread(target=relay,daemon=True)]
    for t in threads:t.start()
    time.sleep(.08)
    sent_at={}
    start=time.monotonic()
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
        for seq in range(count):
            sent_at[seq]=time.monotonic()
            sender.sendto(message(seq),(HOST,RELAY_PORT))
            time.sleep(.003)
    if not relay_done.wait(timeout=max(10,count*(delay_ms/1000+.005)+3)):
        stop.set();raise RuntimeError('UDP relay timed out')
    time.sleep(.35)
    stop.set()
    for t in threads:t.join(timeout=1)
    unique_valid={seq for seq,ok,_ in received if ok}
    corrupt_count=sum(not ok for _,ok,_ in received)
    duplicate_count=len(received)-len({seq for seq,_,_ in received})
    order=[seq for seq,ok,_ in received if ok]
    reordered=sum(order[i]<order[i-1] for i in range(1,len(order)))
    latencies=[(t-sent_at[seq])*1000 for seq,ok,t in received if ok and seq in sent_at]
    return {'protocol':'UDP','sent_packets':count,'received_datagrams':len(received),
            'valid_unique_packets':len(unique_valid),'delivery_ratio_percent':round(100*len(unique_valid)/count,2),
            'corrupted_datagrams':corrupt_count,'duplicate_datagrams':duplicate_count,
            'out_of_order_transitions':reordered,'average_latency_ms':round(sum(latencies)/len(latencies),2) if latencies else None,
            'elapsed_seconds':round(time.monotonic()-start,2)}


def tcp_demo(count:int)->dict:
    records=[]
    ready=threading.Event()
    def server():
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((HOST,TCP_PORT));listener.listen(1);ready.set()
            conn,_=listener.accept()
            with conn:
                buffer=b''
                while len(records)<count:
                    chunk=conn.recv(8192)
                    if not chunk:break
                    buffer+=chunk
                    while len(buffer)>=4:
                        n=struct.unpack('!I',buffer[:4])[0]
                        if len(buffer)<4+n:break
                        packet=buffer[4:4+n];buffer=buffer[4+n:]
                        records.append((struct.unpack('!I',packet[:4])[0],valid(packet)))
    thread=threading.Thread(target=server,daemon=True);thread.start()
    if not ready.wait(2):raise RuntimeError('TCP listener failed')
    start=time.monotonic()
    with socket.create_connection((HOST,TCP_PORT),timeout=5) as client:
        for seq in range(count):
            packet=message(seq)
            client.sendall(struct.pack('!I',len(packet))+packet)
    thread.join(timeout=5)
    return {'protocol':'TCP','sent_messages':count,'received_messages':len(records),
            'valid_messages':sum(ok for _,ok in records),
            'in_order':all(records[i][0]==i for i in range(len(records))),
            'elapsed_seconds':round(time.monotonic()-start,3)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--count',type=int,default=100)
    p.add_argument('--loss',type=float,default=.05,help='0..1 fraction')
    p.add_argument('--delay-ms',type=float,default=2)
    p.add_argument('--corruption',type=float,default=.03)
    p.add_argument('--duplication',type=float,default=.05)
    p.add_argument('--reorder',type=float,default=.1)
    p.add_argument('--seed',type=int,default=7)
    args=p.parse_args()
    if not (1<=args.count<=10000 and 0<=args.delay_ms<=1000 and all(0<=v<=1 for v in (args.loss,args.corruption,args.duplication,args.reorder))):p.error('Invalid parameters')
    results={'tcp':tcp_demo(args.count),'udp':udp_demo(args.count,args.loss,args.delay_ms,args.corruption,args.duplication,args.reorder,args.seed),'configuration':vars(args)}
    out=Path(__file__).resolve().parents[1]/'results';out.mkdir(exist_ok=True)
    (out/'socket_demo.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
