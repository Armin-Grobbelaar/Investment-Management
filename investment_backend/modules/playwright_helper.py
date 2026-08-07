"""
Playwright helper – centralises browser launch logic.

All Playwright-using modules should call ``launch_browser(headless=True)``
instead of ``p.chromium.launch()`` directly so that the correct executable is
always resolved, whether running inside Docker (Playwright-managed chromium) or
on the host system (system-installed chromium / Firefox).

Resolution order (first match wins):
  1. ``PLAYWRIGHT_CHROMIUM_PATH`` environment variable.
  2. Playwright-managed binary in ``~/.cache/ms-playwright/…`` (the default).
  3. ``/usr/bin/chromium`` on the host.
  4. ``None`` → caller gets an ImportError-style error explaining what to do.
"""

from __future__ import annotations
import os
import glob
import logging

logger = logging.getLogger("playwright_helper")

_EXECUTABLE_PATH: str | None = None
_RESOLVED = False


def _resolve() -> str | None:
    global _EXECUTABLE_PATH, _RESOLVED
    if _RESOLVED:
        return _EXECUTABLE_PATH
    _RESOLVED = True

    # 1. Env override
    env_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
    if env_path and os.path.isfile(env_path):
        _EXECUTABLE_PATH = env_path
        return _EXECUTABLE_PATH

    # 2. Playwright-managed binary (fast if already downloaded)
    for pattern in [
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"),
    ]:
        hits = sorted(glob.glob(pattern))
        if hits:
            _EXECUTABLE_PATH = hits[-1]
            return _EXECUTABLE_PATH

    # 3. System chromium on the host
    for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"):
        if os.path.isfile(p):
            _EXECUTABLE_PATH = p
            return _EXECUTABLE_PATH

    logger.warning(
        "No Chromium browser found. Install one of:\n"
        "  • playwright install chromium   (inside a venv)\n"
        "  • pacman -S chromium             (Arch Linux host)\n"
        "  • Set PLAYWRIGHT_CHROMIUM_PATH=/path/to/chromium"
    )
    return None


def chromium_path() -> str | None:
    """Return the resolved chromium executable path, or ``None``."""
    return _resolve()


def launch_browser(headless: bool = True):
    """
    Context-manager-like helper.  Usage::

        with launch_browser() as browser:
            page = browser.new_page()
            ...

    Returns the Playwright Browser instance.  Caller must still ``stop()`` the
    Playwright runtime (or use ``sync_playwright`` as a context manager).

    Returns ``None`` if no browser was found (caller should raise or return early).
    """
    from playwright.sync_api import sync_playwright

    path = _resolve()
    pw = sync_playwright().start()
    kwargs: dict = {"headless": headless}
    if path:
        kwargs["executable_path"] = path
    browser = pw.chromium.launch(**kwargs)
    # Attach pw to browser so caller can stop it later
    browser._pw_runtime = pw  # type: ignore[attr-defined]
    return browser
