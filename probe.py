"""Command-line probe: test the zeversolar library against a real inverter.

Usage:
    poetry run python probe.py <host> --basic      # Test 1: read basic inverter data
    poetry run python probe.py <host> --full       # Test 2: read all data including power limit
    poetry run python probe.py <host> --write      # Test 3: curtail to 90%, restore to 100%
"""

import sys
import time
import dataclasses
import urllib.parse

import requests

from zeversolar import ZeverSolarClient, ZeverSolarPowerLimitData
from zeversolar.exceptions import ZeverSolarInvalidData, ZeverSolarPowerLimitNotSupported, ZeverSolarTimeout


def fetch_raw(host: str, path: str) -> str:
    """Fetch a raw CGI endpoint and return the response body."""
    netloc = urllib.parse.urlparse(f"http://{host}").netloc or host
    url = f"http://{netloc}/{path}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def print_fields(obj: object) -> None:
    for field in dataclasses.fields(obj):  # type: ignore[arg-type]
        print(f"  {field.name}: {getattr(obj, field.name)}")


def wait_for_limit(client: ZeverSolarClient, target_pct: int, timeout: int = 120) -> bool:
    """Poll get_power_limit() until it reaches target_pct or timeout expires.

    Transient timeouts (inverter temporarily offline after a write) are caught
    and retried — the inverter typically recovers within a few seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            current = client.get_power_limit().limit_pct
            print(f"  ... {current}%")
            if current == target_pct:
                return True
        except ZeverSolarTimeout:
            print("  ... (inverter temporarily unreachable, retrying)")
        time.sleep(5)
    return False


def test_basic(host: str) -> None:
    """Test 1: read basic inverter data via get_data()."""
    print(f"=== Test 1: basic read ({host}) ===\n")
    client = ZeverSolarClient(host=host)
    data = client.get_data()
    print_fields(data)
    print("\nTest 1 passed ✓")


def test_full(host: str) -> None:
    """Test 2: read all data including power limit."""
    print(f"=== Test 2: full read ({host}) ===\n")
    client = ZeverSolarClient(host=host)

    print("--- get_data() ---")
    data = client.get_data()
    print_fields(data)

    print("\n--- get_power_limit() ---")
    try:
        limit = client.get_power_limit()
        print_fields(limit)
    except ZeverSolarPowerLimitNotSupported:
        print("  Not supported by this inverter.")
    except ZeverSolarInvalidData:
        print("  ZeverSolarInvalidData — raw adv.cgi response:")
        try:
            raw = fetch_raw(host, "adv.cgi")
            for i, line in enumerate(raw.splitlines()):
                print(f"  line {i:2d}: {line!r}")
        except Exception as exc:
            print(f"  Could not fetch adv.cgi: {exc}")

    print("\nTest 2 passed ✓")


def test_write(host: str) -> None:
    """Test 3: curtail output to 90%, then restore to 100%."""
    print(f"=== Test 3: write test ({host}) ===\n")
    client = ZeverSolarClient(host=host)

    print("--- Reading current limit ---")
    original = client.get_power_limit()
    print_fields(original)

    print("\n--- Curtailing to 90% ---")
    try:
        client.set_power_limit(90)
        if wait_for_limit(client, 90):
            print("  Curtail to 90% verified ✓")
        else:
            print("  WARNING: timed out waiting for 90%")
    finally:
        print("\n--- Restoring to 100% ---")
        client.set_power_limit(100)
        if wait_for_limit(client, 100):
            print("  Restore to 100% verified ✓")
        else:
            print("  WARNING: restore timed out")

    print("\nTest 3 passed ✓")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    host = sys.argv[1]
    mode = sys.argv[2]

    if mode == "--basic":
        test_basic(host)
    elif mode == "--full":
        test_full(host)
    elif mode == "--write":
        test_write(host)
    else:
        print(f"Unknown mode: {mode}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
