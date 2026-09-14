"""Render the saved development-only probe; does not run a model."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--new3', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(r) for r in (args.new3 / 'development_probe.jsonl').read_text().splitlines()]
    x = np.random.RandomState(0).normal(0, .05, (768, 3)).astype(np.float32)
    x[384:640] += 2
    time = np.array([r['t'] for r in rows])
    predictions = np.array([r['forecast'] for r in rows])
    residuals = np.array([r['max_abs_residual'] for r in rows])
    alarms = np.array([r['alarm'] for r in rows])
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.8), sharex=True, layout='constrained')
    for ax in axes:
        ax.axvspan(384, 640, color='#E8B04B', alpha=.18)
        ax.grid(axis='y', alpha=.22)
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].plot(time, x[time, 0], color='#53657A', linewidth=.9, label='Observed channel 1')
    axes[0].plot(time, predictions[:, 0], color='#146B8C', linewidth=1.6, label='TimesFM 3 forecast')
    axes[0].set_ylabel('Value')
    axes[0].legend(loc='upper left', frameon=False)
    axes[0].set_title('A predictable shift soon stops producing large forecast errors', loc='left', fontsize=14, pad=13)
    axes[1].plot(time, residuals, color='#146B8C', linewidth=1.2, label='Maximum absolute error across 3 channels')
    axes[1].axhline(.5, color='#9B3F28', linestyle='--', linewidth=1.2, label='Fixed alarm threshold (0.5)')
    axes[1].scatter(time[alarms], residuals[alarms], color='#9B3F28', s=18, zorder=3)
    axes[1].set_xlabel('Observation index')
    axes[1].set_ylabel('Forecast error')
    axes[1].legend(loc='upper right', frameon=False, fontsize=9)
    axes[1].text(.5, .76, '3 / 256 shifted points alarmed\n0 alarms after the first 32 shifted points', transform=axes[1].transAxes, ha='center', fontsize=10, bbox={'facecolor':'white','edgecolor':'none','alpha':.9})
    fig.suptitle('Development-only synthetic probe; shaded interval is an injected +2 shift, not evidence of malicious intent', fontsize=9, color='#444444')
    args.output.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output / 'new3_persistence.png', dpi=160)
    fig.savefig(args.output / 'new3_persistence.pdf')


if __name__ == '__main__':
    main()
