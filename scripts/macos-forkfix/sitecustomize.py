"""Steer Python's subprocess launches onto posix_spawn instead of fork+exec.

WHY THIS EXISTS
---------------
On macOS 26/27, Apple's Network.framework registers a pthread_atfork *child*
handler (``nw_settings_child_has_forked``) that dereferences freed os_log
preferences and segfaults — in the forked child, after fork() but before exec():

    Thread 0 Crashed:
    0  libsystem_trace.dylib      _os_log_preferences_refresh + 56
    1  libsystem_trace.dylib      os_log_type_enabled + 772
    2  libnetworkextension.dylib  NEFlowDirectorDestroy + 48
    3  Network                    nw_path_release_globals + 148
    4  Network                    nw_settings_child_has_forked() + 292
    5  libsystem_pthread.dylib    _pthread_atfork_child_handlers + 76
    6  libsystem_c.dylib          fork + 112
    7  _posixsubprocess...so      do_fork_exec + 68

Any process that has touched Apple networking is exposed, and `esphome` always
has (git fetches for external_components, media downloads, mDNS). The parent sees
the child exit with signal 11, so the failure surfaces as an ESPHome step failing
with ``returncode=-11`` — most visibly the ESP-IDF Python-env check and venv
creation:

    ERROR Python version - failed (returncode=-11)
    RuntimeError: Can't create Python virtual environment for ESP-IDF 5.5.5

It is a race, so it hits only some forks: an instrumented `esphome compile` ran
24 fork+execs with zero failures once and died on the 15th the next time. See
`logs/python-failure*.log` for captured reports.

posix_spawn does not run atfork handlers at all, so the crash becomes impossible.
CPython already prefers posix_spawn, but only when the Popen call has close_fds
off (macOS has no POSIX_SPAWN_CLOSEFROM), no redirect landing on fd 0-2, cwd None,
and no preexec_fn/pass_fds/shell. ESPHome's calls fail those tests, so this shim
rewrites each call into an equivalent spawn-eligible one:

  * ``stdin``/``stdout``/``stderr`` that merely wrap this process's own fd 0/1/2
    become None — an inherited fd goes to the same place either way;
  * ``close_fds=False`` — already what ESPHome passes on its own subprocess calls;
  * a bare executable name is resolved through PATH, since posix_spawn needs a
    path with a directory separator;
  * ``cwd=DIR`` becomes ``/usr/bin/env -C DIR ...``, because CPython's
    ``os.posix_spawn`` exposes no chdir file action.

Anything it cannot rewrite safely is left exactly as it was, on the fork path.

HOW IT IS LOADED
----------------
``scripts/esphome`` puts this directory on ``PYTHONPATH``; CPython imports any
importable ``sitecustomize`` at startup, so it applies to the esphome process and
to the Python children it spawns (pip, idf.py) without patching the Homebrew
install. Nothing outside that wrapper is affected.

This is a workaround for an OS bug — verify whether it is still needed after a
macOS update, and delete the whole directory once it is not.
"""

import os
import shutil
import subprocess
import sys

_ENV_BIN = "/usr/bin/env"


def _wraps_own_fd(stream, fd: int) -> bool:
    """True if stream is just a wrapper around this process's own fd."""
    if stream is None or isinstance(stream, int):
        return False
    try:
        return stream.fileno() == fd
    except Exception:  # noqa: BLE001  pipes, StringIO, closed streams
        return False


def _install() -> None:
    orig_init = subprocess.Popen.__init__

    def patched_init(self, args, *pargs, **kwargs):
        # Bail on shapes we can't reason about: positional stdio/cwd, shell
        # strings, or calls that already pin their own exec behaviour.
        if (
            pargs
            or isinstance(args, (str, bytes))
            or kwargs.get("shell")
            or kwargs.get("preexec_fn")
            or kwargs.get("pass_fds")
            or kwargs.get("executable")
        ):
            return orig_init(self, args, *pargs, **kwargs)

        try:
            argv = [os.fspath(a) for a in args]
        except TypeError:
            return orig_init(self, args, *pargs, **kwargs)
        if not argv or not all(isinstance(a, str) for a in argv):
            # bytes argv: leave it alone rather than risk mixing str and bytes.
            return orig_init(self, args, *pargs, **kwargs)

        for name, fd in (("stdin", 0), ("stdout", 1), ("stderr", 2)):
            if _wraps_own_fd(kwargs.get(name), fd):
                kwargs[name] = None
        kwargs["close_fds"] = False

        if not os.path.dirname(argv[0]):
            env = kwargs.get("env") or os.environ
            if found := shutil.which(argv[0], path=env.get("PATH")):
                argv[0] = found

        if (cwd := kwargs.get("cwd")) is not None and os.path.dirname(argv[0]):
            argv = [_ENV_BIN, "-C", os.fspath(cwd), *argv]
            kwargs["cwd"] = None

        return orig_init(self, argv, *pargs, **kwargs)

    patched_init._forkfix = True
    subprocess.Popen.__init__ = patched_init


if sys.platform == "darwin" and not getattr(
    subprocess.Popen.__init__, "_forkfix", False
):
    _install()
