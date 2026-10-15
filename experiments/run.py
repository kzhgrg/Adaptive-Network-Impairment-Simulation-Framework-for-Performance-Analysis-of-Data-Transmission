"""Run experiments using native Python by default; optional NS2 backend."""
from __future__ import annotations
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from experiments.native import simulate
from socket_lab.real_experiment import run_real
from analysis.trace import parse_trace, save_metrics, write_summary

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
SCENARIOS = [
    ('baseline',0,10,20,0,0,0),('loss_2',2,10,20,0,0,0),
    ('loss_5',5,10,20,0,0,0),('loss_10',10,10,20,0,0,0),
    ('delay_50',0,50,20,0,0,0),('delay_100',0,100,20,0,0,0),
    ('congested',0,10,5,0,0,0),('corruption_5',0,10,20,5,0,0),
    ('duplication_10',0,10,20,0,10,0),('reordering_20',0,10,20,0,0,20),
    ('combined',3,40,10,3,5,15),
]

def run_one(name, loss, delay, queue, seed=7, corruption=0, duplication=0, reordering=0, engine='native'):
    if not name.replace('_','').replace('-','').isalnum() or len(name)>60:
        raise ValueError('Invalid scenario name')
    RESULTS.mkdir(parents=True,exist_ok=True)
    prefix=RESULTS/name
    events = None
    if engine=='real':
        metrics, events = run_real(loss,delay,queue,seed,corruption,duplication,reordering)
    elif engine=='native':
        metrics=simulate(loss,delay,queue,seed,corruption,duplication,reordering)
    elif engine=='ns2':
        if not shutil.which('ns'): raise RuntimeError('NS2 not installed; choose Native Python engine')
        if any([corruption,duplication,reordering]):
            raise ValueError('NS2 backend only supports loss/delay/queue; use native for other impairments')
        command=['ns',str(ROOT/'ns2'/'tcp_udp.tcl'),str(loss),str(delay),str(queue),str(prefix),str(seed)]
        proc=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=90)
        if proc.returncode: raise RuntimeError(f'NS2 failed: {proc.stderr or proc.stdout}')
        metrics=parse_trace(prefix.with_suffix('.tr'))
    else: raise ValueError('Unknown engine')
    payload={'scenario':name,'engine':engine,'model':('Real TCP/UDP localhost sockets + application relay (not kernel impairment)' if engine=='real' else ('Educational stop-and-wait ARQ vs UDP CBR' if engine=='native' else 'NS2 TCP Reno vs UDP CBR')),
             'loss_percent':loss,'delay_ms':delay,'queue_packets':queue,'seed':seed,
             'corruption_percent':corruption,'duplication_percent':duplication,'reordering_percent':reordering,
             'metrics':metrics}
    if events is not None:
        trace_path = prefix.with_suffix('.events.json')
        trace_path.write_text(json.dumps(events, indent=2), encoding='utf-8')
        payload['event_trace_file'] = trace_path.name
    save_metrics(payload,prefix.with_suffix('.json'))
    return payload

def run_all(seed=7,engine='native'):
    scenarios=SCENARIOS if engine in ('native','real') else SCENARIOS[:7]
    data=[run_one(name,loss,delay,queue,seed,corr,dup,reorder,engine) for name,loss,delay,queue,corr,dup,reorder in scenarios]
    rows=[]
    for entry in data:
        for flow, metrics in entry['metrics'].items():
            rows.append({**{k:v for k,v in entry.items() if k not in ('metrics',)},'flow':flow,**metrics})
    write_summary(rows,RESULTS/'summary.csv')
    (RESULTS/'summary.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--seed',type=int,default=7)
    p.add_argument('--engine',choices=['native','real','ns2'],default='native')
    p.add_argument('--one',nargs=4,metavar=('NAME','LOSS','DELAY','QUEUE'))
    args=p.parse_args()
    if args.one:
        name,loss,delay,queue=args.one
        print(json.dumps(run_one(name,float(loss),float(delay),int(queue),seed=args.seed,engine=args.engine),indent=2))
    else:
        results=run_all(seed=args.seed,engine=args.engine)
        print(f'Completed {len(results)} {args.engine} scenarios; see results/summary.csv')
