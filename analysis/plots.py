"""Generate publication-friendly comparisons from the experiment CSV."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_summary(csv_path, output_dir):
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError('No rows in summary.csv')
    scenarios = list(dict.fromkeys(r['scenario'] for r in rows))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, label, filename in [
        ('throughput_kbps','Throughput (kbps)','throughput.png'),
        ('average_delay_ms','Average one-way delay (ms)','delay.png'),
        ('delivery_ratio_percent','Delivery ratio (%)','delivery_ratio.png'),
        ('unreceived_packets','Packets not received','unreceived_packets.png'),
    ]:
        fig, ax = plt.subplots(figsize=(10,5))
        xs = list(range(len(scenarios)))
        for offset, flow in [(-.19,'tcp'),(.19,'udp')]:
            values = []
            for scenario in scenarios:
                row = next((r for r in rows if r['scenario']==scenario and r['flow']==flow), None)
                values.append(float(row[key]) if row and row[key] else 0)
            ax.bar([x+offset for x in xs],values,width=.38,label=flow.upper())
        ax.set_xticks(xs,scenarios,rotation=25,ha='right')
        ax.set_ylabel(label)
        ax.set_title(f'TCP vs UDP — {label}')
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / filename,dpi=170)
        plt.close(fig)
    print(f'Saved 4 graphs to {output_dir}')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv',default='results/summary.csv')
    parser.add_argument('--out',default='results/plots')
    args=parser.parse_args()
    plot_summary(args.csv,args.out)
