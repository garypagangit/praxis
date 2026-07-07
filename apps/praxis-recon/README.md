# Praxis Recon

Praxis Recon is a static single-page prototype for the Praxis Engine design. It runs directly from `index.html` and stores demo changes in browser `localStorage`.

## Open

Open `apps/praxis-recon/index.html` in a browser.

## Included Views

- Dashboard: metrics, pipeline board, activity feed, budget and gate status.
- Topics: topic creation and active discovery query specs.
- Papers: discovered/reviewed paper queue.
- Ideas: praxis idea scoring and plan export.
- Experiments: plan/run/evaluation status.
- Packages: defense-ready publishing queue.

## Notes

This is a frontend implementation of the workflow console. The backend services from the engineering design, including FastAPI, PostgreSQL, Redis workers, object storage, Claude API calls, and Claude Code sandbox execution, are represented as local state transitions and export actions.

Daily alerts are handled outside the static app by `.github/workflows/praxis-recon-daily.yml`. That workflow runs `scripts/praxis_recon_daily_scan.py`, updates `reports/praxis_recon_daily/`, and opens a GitHub issue when new work is flagged.
