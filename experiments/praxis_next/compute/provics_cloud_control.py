"""Reuse the verified one-shot controller with tighter, explicit acquisition caps.

No AWS call occurs at import. The main command retains the original account,
instance, immutable-input, watchdog, private-transfer, and stop-verification gates.
Legacy descriptive strings mention older limits; the active-run timestamps and
these frozen numeric limits are authoritative for this narrower acquisition job.
"""
from experiments.apt_final.native_graph import cloud_control as control

control.TOTAL_SECONDS = 2700          # 45 minutes to observed stop, outer ceiling
control.WATCHDOG_SECONDS = 2400       # independent stop request at 40 minutes
control.WORKER_DEADLINE_SECONDS = 1800  # work/publication done by 30 minutes
control.MAX_COMMAND_SECONDS = 1500
control.INCIDENTAL_ALLOWANCE_USD = .75
control.TOTAL_RESERVE_USD = 2.00

Controller = control.Controller

if __name__ == '__main__':
    raise SystemExit(control.main())
