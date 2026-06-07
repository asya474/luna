"""Payment ID generation per QIWI documentation."""

from __future__ import annotations

import time


def generate_payment_id() -> str:
    """
    Generate a unique client payment ID.

    Docs recommend: id = 1000 * Unix timestamp (seconds), max 20 digits.
    We use milliseconds timestamp as shown in official Python examples.
    """
    return str(int(time.time() * 1000))
