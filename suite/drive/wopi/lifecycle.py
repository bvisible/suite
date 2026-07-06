"""
Collabora coolwsd lifecycle management — start on-demand, stop when idle.

The Collabora `coolwsd` daemon spawns 4 prespawned LibreOffice kit workers
plus the main process and consumes ~150-200 MB RSS + up to 1 GB of swap on
small-RAM Neoffice instances even when no document is being edited. To avoid
this idle cost, we disable the systemd unit at boot (so it does not start
automatically) and start it lazily when drive_wopi is asked to serve an
editor URL.

Lifecycle:
- ``ensure_running()`` is called from :func:`suite.drive.wopi.discovery`
  before any HTTP request to coolwsd. If the unit is inactive it issues
  ``sudo systemctl start coolwsd`` and polls ``/hosting/discovery`` until
  the daemon responds (typical cold start: 5-10 s).
- Each successful start updates the ``collabora_last_activity`` Redis key
  (TTL 24 h) so the idle watchdog knows when the last user touched it.
- ``stop_if_idle()`` is wired into Frappe's cron scheduler. Every 5 min it
  checks for active TCP connections to 127.0.0.1:9980 and the timestamp
  of last activity; if no connection is open and the table has been silent
  for ``COLLABORA_IDLE_SECONDS`` (default 900 = 15 min) it stops coolwsd
  via ``sudo systemctl stop coolwsd``.

Required permissions: the user running Frappe (``neoffice``) must have
NOPASSWD sudo for exactly three commands — ``systemctl start coolwsd``,
``systemctl stop coolwsd``, ``systemctl is-active coolwsd``. The sudoers
file is dropped by :func:`suite.drive.wopi (install helper)` at
``after_install`` and ``after_migrate``.

Failure mode: if the start command fails (sudoers misconfigured, package
missing) the helper logs a Frappe error and returns ``False``. The caller
in ``discovery.py`` then surfaces a "Collabora server not available"
message to the editor UI rather than hanging.
"""

from __future__ import annotations

import socket
import subprocess
import time
from typing import Optional
from urllib import request as urlrequest
from urllib.error import URLError

import frappe


# Activity key in Frappe cache (Redis-backed). The watchdog refuses to stop
# coolwsd if this key is younger than COLLABORA_IDLE_SECONDS.
COLLABORA_LAST_ACTIVITY_KEY = "collabora:last_activity"

# How long we wait for ``/hosting/discovery`` to come up after issuing
# ``systemctl start coolwsd``. The cold-start path on a swapped-out 4 GB
# instance is dominated by Python kit-worker prespawn + LibreOffice template
# load; 20 s is comfortable while still failing fast in pathological cases.
COLLABORA_START_TIMEOUT_SECONDS = 20

# How long we tolerate idleness before stop_if_idle() will shut the daemon
# down. Must comfortably exceed the longest expected gap between user
# interactions during a single editing session — Collabora itself sends
# keep-alives every ~10 s, so any value above ~30 s is safe; 15 min lets
# users step away to a meeting without losing their session.
COLLABORA_IDLE_SECONDS = 15 * 60

# Address coolwsd binds to. Must match the upstream config in
# /etc/coolwsd/coolwsd.xml; we listen on loopback because nginx proxies
# externally.
COOLWSD_HOST = "127.0.0.1"
COOLWSD_PORT = 9980


def _systemctl(action: str, timeout: int = 10) -> tuple[bool, str]:
    """Run ``sudo -n systemctl <action> coolwsd`` and return (ok, output).

    ``-n`` makes sudo fail loudly instead of prompting if sudoers is wrong;
    the caller can then degrade gracefully.
    """
    try:
        completed = subprocess.run(
            ["sudo", "-n", "systemctl", action, "coolwsd"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout running systemctl {action} coolwsd"
    except FileNotFoundError:
        return False, "sudo or systemctl not found on PATH"

    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode == 0, output.strip()


def is_coolwsd_active() -> bool:
    """True iff systemd reports coolwsd as active."""
    ok, _output = _systemctl("is-active", timeout=5)
    return ok


def _can_connect_socket(timeout: float = 1.0) -> bool:
    """True iff coolwsd is accepting TCP connections on its port."""
    try:
        with socket.create_connection((COOLWSD_HOST, COOLWSD_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def _discovery_responds(timeout: float = 1.0) -> bool:
    """True iff /hosting/discovery returns HTTP 200 (full readiness probe).

    The TCP port can be open while coolwsd is still loading the LibreOffice
    template, in which case /hosting/discovery returns 503 / never responds.
    Probing the actual application endpoint instead of just the socket
    eliminates the race where ensure_running() declares the daemon ready a
    second or two before it can serve a real request — the symptom we saw
    on Osiris was the user's first double-click landing on a "Collaborative
    editing not available" modal because check_collabora_status() ran
    before the daemon could parse the discovery XML.
    """
    url = f"http://{COOLWSD_HOST}:{COOLWSD_PORT}/hosting/discovery"
    try:
        with urlrequest.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False
    except Exception:  # noqa: BLE001 — defensive; never raise from a probe
        return False


def _record_activity() -> None:
    """Mark coolwsd as recently used so the idle watchdog backs off."""
    cache = frappe.cache()
    # 24 h TTL is generous: even if scheduler is off, the key naturally
    # expires within a day and the watchdog can act again.
    cache.set_value(COLLABORA_LAST_ACTIVITY_KEY, int(time.time()), expires_in_sec=86400)


def _last_activity() -> Optional[int]:
    """Return Unix-time of last recorded activity, or None if never seen."""
    raw = frappe.cache().get_value(COLLABORA_LAST_ACTIVITY_KEY)
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _count_active_websockets() -> int:
    """Count established TCP connections to coolwsd's port.

    We rely on ``ss -Htan state established`` because it is in coreutils on
    every Debian/Ubuntu host we deploy on, requires no extra package, and
    does not depend on coolwsd's admin socket (which is opt-in and
    typically off in our nginx setup).

    A non-zero count means at least one user has an editor tab open; we
    must not stop the service.
    """
    try:
        completed = subprocess.run(
            ["ss", "-Htan", "state", "established", f"sport = :{COOLWSD_PORT}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Be conservative: if we cannot count, assume active.
        return 1

    if completed.returncode != 0:
        return 1

    lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
    return len(lines)


def ensure_running(timeout: int = COLLABORA_START_TIMEOUT_SECONDS) -> bool:
    """Make sure coolwsd is up AND fully serving /hosting/discovery.

    Returns True on success, False if start failed or the daemon never
    answered an HTTP probe within ``timeout`` seconds. Probes the discovery
    endpoint (not just the TCP socket) so the caller can rely on
    /hosting/discovery returning 200 immediately after this returns —
    which is what check_collabora_status() does next.
    """
    if is_coolwsd_active() and _discovery_responds():
        _record_activity()
        return True

    ok, output = _systemctl("start", timeout=timeout)
    if not ok:
        frappe.log_error(
            "Collabora start failed",
            f"sudo systemctl start coolwsd returned non-zero: {output[:1000]}",
        )
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        # Wait for full readiness, not just the TCP listener — the daemon
        # binds the port well before it can answer a discovery request,
        # and the gap was long enough on Osiris (~3 s under swap pressure)
        # that the frontend's first call landed in the wrong state.
        if _discovery_responds():
            _record_activity()
            return True
        time.sleep(0.5)

    frappe.log_error(
        "Collabora start timeout",
        f"coolwsd started but /hosting/discovery did not return 200 within {timeout}s",
    )
    return False


def stop_if_idle() -> dict:
    """Cron entry point — stop coolwsd if no active sessions for COLLABORA_IDLE_SECONDS.

    Returns a structured result useful for logs / debugging:
        ``{ "action": "stopped" | "kept" | "noop", "reason": "<why>" }``.

    The function never raises. Idempotent: a no-op when coolwsd is already
    inactive.
    """
    if not is_coolwsd_active():
        return {"action": "noop", "reason": "coolwsd already inactive"}

    active_sockets = _count_active_websockets()
    if active_sockets > 0:
        _record_activity()
        return {"action": "kept", "reason": f"{active_sockets} active connection(s)"}

    last = _last_activity()
    now = int(time.time())
    if last is None:
        # No activity ever recorded since boot AND no connections right now.
        # Most likely scenario: coolwsd was started by something other than
        # drive_wopi (a manual systemctl, a unit override) and nobody used
        # it. We stop it conservatively after a single grace period.
        last = now - COLLABORA_IDLE_SECONDS - 1

    idle_for = now - last
    if idle_for < COLLABORA_IDLE_SECONDS:
        return {
            "action": "kept",
            "reason": f"last activity {idle_for}s ago < {COLLABORA_IDLE_SECONDS}s threshold",
        }

    ok, output = _systemctl("stop", timeout=10)
    if not ok:
        frappe.log_error(
            "Collabora stop failed",
            f"sudo systemctl stop coolwsd returned non-zero: {output[:1000]}",
        )
        return {"action": "kept", "reason": f"systemctl stop failed: {output[:200]}"}

    return {
        "action": "stopped",
        "reason": f"idle for {idle_for}s, no active connections",
    }
