"""AddressBundle — the resolved per-address input every OSINT source
module receives (docs/address_osint_assistant_design.md §Inputs).

Resolution paths:
  * --pid N            -> spine lookup (address forms + geocoded point)
  * --address "..."    -> building_key match against the spine (local, no
                          network); off-spine addresses additionally need
                          --lat/--lon (P0 has no live-geocode fallback --
                          Engine 2's Yandex/Visicom geocoders are P1).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from ..normalize.address import address_to_building_key
from .variants import Variant, expand_variants, slugify

log = logging.getLogger(__name__)


@dataclass
class AddressBundle:
    pid: int | None
    building_id: str | None
    prewar_address: str | None
    occupation_address: str | None
    lat: float
    lon: float
    slug: str
    variants: list[Variant] = field(default_factory=list)
    geocode_note: str | None = None

    def summary(self) -> dict:
        return {
            "pid": self.pid,
            "building_id": self.building_id,
            "prewar_address": self.prewar_address,
            "occupation_address": self.occupation_address,
            "lat": self.lat,
            "lon": self.lon,
            "slug": self.slug,
            "geocode_note": self.geocode_note,
            "n_variants": len(self.variants),
            "variants": [v.text for v in self.variants[:25]],
        }


def _split_street_house(address: str) -> tuple[str, str | None]:
    """Split a free-text address into (street, house). First comma wins
    (project rule: split on FIRST comma); else last standalone number token."""
    address = address.strip()
    if "," in address:
        street, _, rest = address.partition(",")
        m = re.search(r"(\d+\s*[/\-]?\s*\d*\s*[а-яА-ЯёЁa-zA-Z]?)\s*$", rest.strip())
        return street.strip(), (m.group(1).strip() if m else rest.strip() or None)
    m = re.search(r"^(.*?)[\s,]+(?:д\.?\s*)?(\d+[а-яА-ЯёЁa-zA-Z]?(?:/\d+)?)\s*$", address)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return address, None


def resolve_bundle(
    pid: int | None = None,
    address: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> AddressBundle:
    """Resolve to a full AddressBundle. Raises ValueError with a clear
    message when resolution is impossible without network geocoding."""
    from .. import config  # deferred: keeps module importable without .env

    if pid is None and not address:
        raise ValueError("need --pid or --address")

    row = None
    import psycopg2

    con = psycopg2.connect(config.DATABASE_URL)
    try:
        cur = con.cursor()
        if pid is not None:
            cur.execute(
                """SELECT id, building_id, prewar_address, occupation_address,
                          ST_Y(ST_Centroid(geom::geometry)), ST_X(ST_Centroid(geom::geometry))
                   FROM property WHERE id = %s""",
                (pid,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"property_id {pid} not on spine")
        else:
            street, house = _split_street_house(address)
            key = address_to_building_key(street, house)
            if key:
                cur.execute(
                    """SELECT id, building_id, prewar_address, occupation_address,
                              ST_Y(ST_Centroid(geom::geometry)), ST_X(ST_Centroid(geom::geometry))
                       FROM property WHERE building_id = %s""",
                    (key,),
                )
                row = cur.fetchone()
            if row is None:
                glat, glon = lat, lon
                geo_note = None
                if glat is None or glon is None:
                    # off-spine + no explicit point -> live-geocode (Engine 2)
                    from .geocode import geocode
                    gr = geocode(address)
                    if gr is None:
                        raise ValueError(
                            f"address {address!r} (key={key}) not on spine and "
                            "no geocoder resolved it — pass --lat/--lon explicitly"
                        )
                    glat, glon = gr.lat, gr.lon
                    geo_note = (f"geocoded via {gr.source} (confidence={gr.confidence}"
                                + (f", spread={gr.max_spread_m}m" if gr.max_spread_m else "")
                                + ")")
                    log.info("off-spine %r -> (%.6f,%.6f) %s", address, glat, glon, geo_note)
                b = AddressBundle(
                    pid=None, building_id=key,
                    prewar_address=None, occupation_address=address,
                    lat=glat, lon=glon,
                    slug=slugify(None, key or address),
                )
                b.variants = expand_variants(None, address)
                if geo_note:
                    b.geocode_note = geo_note
                return b
    finally:
        con.close()

    r_pid, r_key, r_prewar, r_occ, r_lat, r_lon = row
    if r_lat is None or r_lon is None:
        if lat is None or lon is None:
            raise ValueError(
                f"property {r_pid} has no geometry on spine — pass --lat/--lon"
            )
        r_lat, r_lon = lat, lon
    b = AddressBundle(
        pid=r_pid, building_id=r_key,
        prewar_address=r_prewar, occupation_address=r_occ,
        lat=float(r_lat), lon=float(r_lon),
        slug=slugify(r_pid, r_key or r_occ or r_prewar or "unknown"),
    )
    b.variants = expand_variants(r_prewar, r_occ)
    log.info("bundle: pid=%s key=%s point=(%.6f, %.6f) variants=%d",
             b.pid, b.building_id, b.lat, b.lon, len(b.variants))
    return b
