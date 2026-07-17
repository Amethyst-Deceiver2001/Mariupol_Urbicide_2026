#!/usr/bin/env python3
"""Shadow-angle date/time verification for a KNOWN location.

Bellingcat's ShadowFinder (github.com/bellingcat/ShadowFinder) solves the
opposite problem: given a known date/time + a shadow measurement, it finds
WHERE on Earth that shadow could occur — built for photos where the
location is unknown. This project's photos/videos are the other way
around: the ADDRESS is known (a spine pid, or explicit lat/lon), and what's
in question is whether a CLAIMED date/time on a Telegram post or YouTube
video is consistent with the shadow angle visible in the frame.

That's a direct solar-position calculation (pysolar), not a location
search, so this is a small purpose-built script rather than a wrapper
around ShadowFinder's machinery.

Two modes:
  verify — you have a claimed UTC date/time AND a shadow measurement
           (object height + shadow length, or a directly-measured sun
           altitude in degrees). Reports the actual sun altitude at that
           place/time and whether it's consistent with the measurement.
  scan   — you have a shadow measurement but an uncertain/disputed date.
           Scans a date, hour by hour (UTC), and lists times whose
           predicted altitude falls within tolerance of the measured one.

Height/shadow-length are unitless ratios (metres, pixels, whatever — only
the ratio matters): altitude_deg = atan(height / shadow_length).

Usage:
    # verify a claimed timestamp against a shadow measurement
    PYTHONPATH=src .venv312/bin/python scripts/327_shadow_angle_dating.py verify \
        --pid 4837 --claimed-utc 2022-04-21T11:30:00 \
        --object-height 10 --shadow-length 14.2

    # scan a whole day for times consistent with the measured shadow
    PYTHONPATH=src .venv312/bin/python scripts/327_shadow_angle_dating.py scan \
        --pid 4837 --date 2022-04-21 --altitude-deg 35.2 --tolerance-deg 2

Install: pip install -e '.[sunpos]'
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _location(args) -> tuple[float, float, str]:
    if args.pid is not None:
        from mariupol_seizures.osint.bundle import resolve_bundle
        b = resolve_bundle(pid=args.pid)
        return b.lat, b.lon, (b.occupation_address or b.prewar_address or f"pid={args.pid}")
    if args.lat is not None and args.lon is not None:
        return args.lat, args.lon, f"({args.lat},{args.lon})"
    print("need --pid or --lat/--lon", file=sys.stderr)
    sys.exit(1)


def _altitude_from_shadow(args) -> float:
    if args.altitude_deg is not None:
        return args.altitude_deg
    if args.object_height and args.shadow_length:
        return math.degrees(math.atan(args.object_height / args.shadow_length))
    print("need --altitude-deg, or both --object-height and --shadow-length",
         file=sys.stderr)
    sys.exit(1)


def cmd_verify(args) -> None:
    try:
        from pysolar.solar import get_altitude, get_azimuth
    except ImportError:
        print("pysolar not installed — pip install -e '.[sunpos]'", file=sys.stderr)
        sys.exit(1)

    lat, lon, label = _location(args)
    measured_alt = _altitude_from_shadow(args)
    when = dt.datetime.fromisoformat(args.claimed_utc).replace(tzinfo=dt.timezone.utc)

    actual_alt = get_altitude(lat, lon, when)
    actual_az = get_azimuth(lat, lon, when)
    diff = abs(actual_alt - measured_alt)

    print(f"\nlocation: {label} ({lat:.6f}, {lon:.6f})")
    print(f"claimed UTC time: {when.isoformat()}")
    print(f"measured shadow → sun altitude: {measured_alt:.1f}°")
    print(f"actual sun altitude at that place/time: {actual_alt:.1f}°  "
         f"(azimuth {actual_az:.1f}°)")
    print(f"difference: {diff:.1f}°")
    if actual_alt < 0:
        print("VERDICT: sun is below horizon at this claimed time — "
             "a visible shadow is IMPOSSIBLE. Claimed time is inconsistent.")
    elif diff <= args.tolerance_deg:
        print(f"VERDICT: consistent (within ±{args.tolerance_deg}° tolerance)")
    else:
        print(f"VERDICT: INCONSISTENT — off by {diff:.1f}°, exceeds "
             f"±{args.tolerance_deg}° tolerance. Claimed time is questionable.")


def cmd_scan(args) -> None:
    try:
        from pysolar.solar import get_altitude
    except ImportError:
        print("pysolar not installed — pip install -e '.[sunpos]'", file=sys.stderr)
        sys.exit(1)

    lat, lon, label = _location(args)
    measured_alt = _altitude_from_shadow(args)
    date = dt.date.fromisoformat(args.date)

    print(f"\nlocation: {label} ({lat:.6f}, {lon:.6f})")
    print(f"measured shadow → sun altitude: {measured_alt:.1f}°  "
         f"(±{args.tolerance_deg}° tolerance)")
    print(f"scanning {date.isoformat()} UTC, every {args.step_minutes} min:\n")

    hits = []
    t = dt.datetime.combine(date, dt.time(0, 0), tzinfo=dt.timezone.utc)
    end = t + dt.timedelta(days=1)
    while t < end:
        alt = get_altitude(lat, lon, t)
        if alt >= 0 and abs(alt - measured_alt) <= args.tolerance_deg:
            hits.append((t, alt))
        t += dt.timedelta(minutes=args.step_minutes)

    if not hits:
        print("no times this day match the measured shadow within tolerance "
             "(check the shadow measurement, or the sun never reaches that "
             "altitude at this location/season)")
        return
    for t, alt in hits:
        print(f"  {t.strftime('%H:%M')} UTC  →  altitude {alt:.1f}°  "
             f"(diff {abs(alt-measured_alt):.1f}°)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--pid", type=int, help="spine property_id for location")
        p.add_argument("--lat", type=float)
        p.add_argument("--lon", type=float)
        p.add_argument("--object-height", type=float,
                       help="known/estimated object height (any unit)")
        p.add_argument("--shadow-length", type=float,
                       help="measured shadow length (same unit as height)")
        p.add_argument("--altitude-deg", type=float,
                       help="sun altitude in degrees, if already computed "
                            "(overrides --object-height/--shadow-length)")
        p.add_argument("--tolerance-deg", type=float, default=2.0)

    pv = sub.add_parser("verify", help="check a claimed UTC timestamp against the shadow")
    add_common(pv)
    pv.add_argument("--claimed-utc", required=True,
                    help="ISO datetime, UTC, e.g. 2022-04-21T11:30:00")
    pv.set_defaults(func=cmd_verify)

    ps = sub.add_parser("scan", help="scan a day for times matching the shadow")
    add_common(ps)
    ps.add_argument("--date", required=True, help="YYYY-MM-DD (UTC)")
    ps.add_argument("--step-minutes", type=int, default=10)
    ps.set_defaults(func=cmd_scan)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
