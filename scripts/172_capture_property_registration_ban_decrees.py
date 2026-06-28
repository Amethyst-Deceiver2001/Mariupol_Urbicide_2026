#!/usr/bin/env python3
"""Capture press confirmation of the 3-decree property-registration-ban
chain (No. 1103 / 145 / 1006) found via @mrpl_besxozxata chat analysis.
Quick HTML fetches, no network-heavy work -- safe to run directly.
"""
import sys; sys.path.insert(0,'src')
from mariupol_seizures import config, forensics
import requests

con = forensics.open_state()
targets = [
    {
        "url": "https://ppt.ru/obzory/vstupaet-v-silu/ukaz-prezidenta-rf-29-12-2025-1006",
        "source_type": "press_article",
        "title": "PPT.ru summary: Ukaz Prezidenta RF No. 1006 (29.12.2025)",
        "description": "Third decree in the property-dispossession-by-decree chain found via "
            "@mrpl_besxozxata chat analysis. Bans NOTARIZATION of powers of attorney "
            "(and other legally significant acts) concerning real estate in DNR/LNR/"
            "Zaporizhzhia/Kherson for citizens of 'unfriendly states', without special "
            "permission, through 31.12.2027 -- directly targets the доверенность/POA "
            "route residents in the chat were relying on as their last defense against "
            "ownerless designation. References exempted categories defined in Ukaz No. "
            "1103's point 2(2), subsections (a)-(g).",
        "content_type": "text/html",
    },
    {
        "url": "https://rg.ru/documents/2025/03/17/yurlica-novye-regiony.html",
        "source_type": "press_article",
        "title": "Rossiyskaya Gazeta: Ukaz Prezidenta RF No. 145 (14.03.2025) full text/summary",
        "description": "Second decree in the chain -- amends Ukaz No. 1103 (24.12.2024). "
            "Bans property-rights registration for citizens of 'unfriendly states' in "
            "DNR/LNR/Zaporizhzhia/Kherson without special permission, through 01.01.2028 "
            "(legal-entity registration ban separately through 01.01.2026). Exemptions "
            "from the special-permission requirement are narrowly carved for foreign "
            "military contractors serving in the Russian armed forces, foreign soldiers "
            "discharged after 24.02.2022 for specific reasons, and their spouses/children/"
            "parents -- i.e. military-service-linked persons only, not ordinary civilian "
            "owners. A 'collegial body' decides special-permission requests (the basis "
            "for what @mrpl_besxozxata residents call 'СРК' -- Специальная региональная "
            "комиссия); decisions communicated within 3 business days to territorial tax/"
            "cadastral offices.",
        "content_type": "text/html",
    },
]
for t in targets:
    try:
        r = requests.get(t["url"], headers={"User-Agent": config.USER_AGENT}, timeout=20)
    except requests.RequestException as e:
        print("FAIL", t["url"], e); continue
    if r.status_code != 200:
        print("HTTP", r.status_code, t["url"]); continue
    sha = forensics.capture_source(
        r.content, url=t["url"], source_type=t["source_type"], title=t["title"],
        description=t["description"], content_type=r.headers.get("Content-Type","text/html"),
        http_status=r.status_code, con=con,
    )
    print("captured", t["url"], "->", sha[:12])
con.close()
