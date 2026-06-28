#!/usr/bin/env python3
"""Capture remaining quick research targets from the registration-ban-decree
and ownerless-registry leads found via @mrpl_besxozxata chat analysis.
Quick HTML fetches only -- safe to run directly.
"""
import sys; sys.path.insert(0,'src')
from mariupol_seizures import config, forensics
import requests

con = forensics.open_state()
targets = [
    {
        "url": "https://gb-dnr.ru/normative-base/detail/2268",
        "source_type": "press_article",
        "title": "GB-DNR normative-base: consolidated text of Ukaz No. 1103 (24.12.2024, as amended)",
        "description": "Consolidated/current text reflecting amendments No. 145 and No. 1006 "
            "folded into the base decree: legal-entity registration ban (until 15.03.2027), "
            "property-rights registration ban (until 01.01.2028), AND notarial-action/POA "
            "ban (until 01.01.2028, harmonized date) for unfriendly-state citizens in DNR/"
            "LNR/Zaporizhzhia/Kherson. Exemptions: foreign military volunteers enlisted "
            "after 24.02.2022, discharged servicemembers meeting criteria, their spouses/"
            "children/parents, and family members of Russian SVO participants. Regional "
            "collegial bodies (= 'СРК' in chat parlance) issue special permits, can deny "
            "on national-defense/security grounds.",
        "content_type": "text/html",
    },
    {
        "url": "https://mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/ownerless/",
        "source_type": "press_article",
        "title": "Mariupol municipal ownerless-property official explainer page",
        "description": "Official municipal page: legal basis закон ДНР №66-РЗ (21.03.2024); "
            "properties registered with Rosreestr are automatically excluded from the "
            "ownerless list on confirmation, regardless of prior listing; district-level "
            "Excel lists (Ordzhonikidze/Primorsk/Ilyichevsk/Zhovtnevy, as of 17.03.2026); "
            "references 107 administrative orders (recognitions + exclusions). Contact: "
            "+7(949)500-93-39 ext.113, adm@mariupol.gov-dpr.ru, Gromovaya St. 63.",
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
