"""Verified Telegram building-chat -> spine building mapping.

Each per-chat parser script (88,91,94,98,102,104,122,123,135-147) already
hand-verified which spine property_id(s) its channel covers -- that's the
authoritative source, not the channel's free-text title (titles are often
multi-building, abbreviated, or carry no street-type word at all, e.g. "Мира
111", "Морской 20", "Металлургов 71,73" -- title-guessing via
address_to_building_key() silently fails or mis-resolves most of these).

This module hand-extracts those pid lists (CHAT_PIDS) plus a small fallback
for the handful of chats whose parser never assigned spine pids but whose
canonical street+houses are documented in their own docstring
(CHAT_STREET_HOUSES), so callers can resolve a chat to its real building(s)
without re-parsing the title.

Built 2026-06-18 while cross-referencing script 151's media-lifecycle
manifest against the spine for case-study candidate scoring (script 153) and
evidence loading (script 152). Extend this table when adding new per-chat
parsers; do not fall back to title-guessing for a chat that's listed here.
"""
from __future__ import annotations

# chat slug -> list of already-verified spine property ids covered by that
# channel (from each parser script's own PIDS/HOUSE_PIDS dict or docstring).
CHAT_PIDS: dict[str, list[int]] = {
    "invite_ucWZaRSL1Gk1NjRi": [4648],                                   # 122 Stroiteley92
    "invite_ooUT61cOOFZjMDcy": [7027, 7207, 7028, 5969, 5970, 5971, 5972,
                                  5973, 7186, 5963, 5964, 5965, 5966, 5967,
                                  7185, 5968],                            # 123 Kronshtadtskaya
    "invite_jWgnL94OdmYmMy": [4424, 4425],                               # 135 Mira111
    "mariupol_komsomolets": [10625, 4780, 4781, 4782],                   # 136
    "metalurgov89_91": [4550, 4551],                                     # 137
    "invite_rBQJ4lUIDZc5YTUy": [4527, 4528, 4787, 4789, 4472],           # 138
    "invite_ZPLyCLn2RItmNWMy": [10714, 10715],                          # 139
    "nahimova_lavitskogo": [5842, 5843, 5844, 5987, 5989],               # 140
    "invite_DCg6OyadlYYyYjc6": [],                                       # 141 -- no spine pid yet
    "invite_gxgwA2by644ZTAy": [5038, 5303, 5043, 6832, 5097, 5269],      # 142
    "metallgov": [4539, 4540],                                           # 143
    "budivelnikiv": [],                                                  # 144 -- no spine pid yet
    "shevchenko74mariupol": [4399],                                      # 145
    "invite_SWCkzbFpPJBkODBi": [4920, 4921, 4922, 4923, 4924, 6110],     # 146
    "invite_Xr0WjIQ8rOU2NmYy": [6258],                                   # 147
    "Mitropolitskaya102": [13982, 10654, 10655, 10656],                  # 102
    "morskoy_38_36_30": [10724],                                         # 77 (д.30/36 not in spine)
    "invite_ki8JvbQallmMzg6": [6109, 4774, 4775, 6247],                  # 104 Bakhchivandzhi13-17
    "Lenina106_Mariupol": [4419],                                        # 94
    "kuprina33": [4939],                                                 # 88
    "invite_LXDgwK2VGAE4MWVh": [4401, 4402],                             # 91 Shevchenko77/79
    "morskoy_48": [10718, 10724, 5071],                                  # 98
    "invite_QaRRTdUZFw0OTU6": [10704, 10707],                           # 96 Meotidy15/20
}

# chats with no spine pid recorded by their parser, but a canonical
# street+house list documented in the parser's own docstring -- resolved via
# address_to_building_key() against the explicit, known-correct address (not
# the free-text channel title).
CHAT_STREET_HOUSES: dict[str, tuple[str, list[str]]] = {
    "olimpiyskaya_71_79": ("улица Олимпийская", ["71", "73", "75", "77", "79"]),
    "stroiteley_175_177_163_171_166_152": ("проспект Строителей",
                                            ["175", "177", "163", "171", "166", "152"]),
    "Azovstalskaya31": ("улица Азовстальская", ["31"]),
}
