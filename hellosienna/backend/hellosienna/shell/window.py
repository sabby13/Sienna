"""pywebview window (M0). Kept import-light: pywebview is imported inside the
functions so importing this module never requires a system webview (headless/CI).
"""

from __future__ import annotations

from typing import Callable


def open_window(url: str, on_closed: Callable[[], None] | None = None) -> None:
    """Open the native window pointed at the local SPA URL and block until closed.

    Raises ImportError if pywebview is unavailable (e.g. headless container) — the
    caller decides how to handle that. This is the only place pywebview is used.
    """
    import webview  # local import: not needed outside the real desktop launch

    window = webview.create_window("HelloSienna", url)
    if on_closed is not None:
        window.events.closed += on_closed
    webview.start()
