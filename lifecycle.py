import atexit
import glob
import os
import signal
import sys

_registered = []


def register_teardown(*callables):
    for fn in callables:
        _registered.append(fn)
        atexit.register(fn)


def _handle(signum, frame):
    for fn in reversed(_registered):
        try:
            fn()
        except Exception:
            pass
    sys.exit(0)


def install_signal_handlers():
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except Exception:
            pass


def cleanup_traces(exe_name):
    system_root = os.environ.get('SystemRoot', r'C:\Windows')
    prefetch = os.path.join(system_root, 'Prefetch')
    removed = 0
    for f in glob.glob(os.path.join(prefetch, exe_name + '*.pf')):
        try:
            os.remove(f)
            removed += 1
        except Exception:
            pass
    return removed