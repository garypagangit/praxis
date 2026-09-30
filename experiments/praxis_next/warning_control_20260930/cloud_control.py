"""Use established controller with this batch's explicit allocation bounds."""
from experiments.apt_final.native_graph import cloud_control as control
control.TOTAL_SECONDS=2700
control.WATCHDOG_SECONDS=2400
control.WORKER_DEADLINE_SECONDS=1800
control.MAX_COMMAND_SECONDS=1500
control.INCIDENTAL_ALLOWANCE_USD=.75
control.TOTAL_RESERVE_USD=2.
if __name__=='__main__':raise SystemExit(control.main())
