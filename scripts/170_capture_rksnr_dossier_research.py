#!/usr/bin/env python3
"""Capture RKS-NR / RosKapStroy / Dossier Center research artifacts confirming
the federal-level stakeholder chain behind the Troianda-M / Metallurgov 47
replacement project (Sharipov, Khusnullin, the ownerless-registry pipeline's
quantified scale). Quick HTML fetches only -- safe to run directly.
"""
import sys; sys.path.insert(0,'src')
from mariupol_seizures import config, forensics
import requests

con = forensics.open_state()
targets = [
    {
        "url": "https://echofm.online/statya-dnya/dose-mariupolskij-peredel-v-okkupirovannom-gorode-otbirayut-kvartiry-dazhe-u-storonnikov-rossii-i-peredayut-silovikam",
        "source_type": "press_article",
        "title": "Echo FM mirror of Dossier Center investigation: Mariupol redistribution",
        "description": "Mirrors dossier.center/mariupol/ (blocked 403 direct). Major macro-context "
            "investigation: ownerless-registry pipeline quantified (6,842 apartments on "
            "potential seizure list as of 01.11.2025, growing weekly; 22,667 apartments in "
            "366 demolished buildings; 10,461 families with compensation claims; 5,320 "
            "replacement municipal units, 5,141-unit shortfall slated to be filled with "
            "seized 'bezkhoznaya' apartments; 6,004 apartments in 43+ commercial projects "
            "sold via 2%% mortgages). Seizure-recipient priority groups named: prosecutor's "
            "office staff, Investigative Committee, FSB, police, emergency services, 'SVO "
            "veterans' -- direct sourced evidence for Rome Statute 8(2)(b)(viii) population "
            "transfer to security personnel specifically. Named officials: Marat Khusnullin "
            "(Хуснуллин, Deputy PM, oversees occupied-territory construction -- CORRECTS "
            "earlier session's 'Khusnutdinov' transcription error), Ildar Sharipov (RKS-NR "
            "director, also paid by Moscow's Moskapstroy, considered Khusnullin's domain), "
            "Anton Koltsov (occupation head of Mariupol), Evgeny Balitsky (Zaporizhzhia "
            "'governor', quoted: history will judge if we were right, but we're giving these "
            "[seized] objects to [security forces]), Dmitry Sablin (Russian MP, GRU-linked, "
            "tied to criminal figure Petr Ivanov), Roman Tesluk (crypto intermediary in a "
            "~$6,500 retroactive-ownership scheme using Ukrainian notary docs re-registered "
            "under Russian law). Petr Andryushchenko named as an independent Ukrainian source "
            "(Center for Occupation Studies), not a perpetrator.",
        "content_type": "text/html",
    },
    {
        "url": "https://xn----stbkjdd.xn--p1ai/company/",
        "source_type": "press_article",
        "title": "RKS-NR official site (rks-nr.ru, redirects to Cyrillic IDN domain)",
        "description": "Company self-description: subsidiary of FAU RosKapStroy, founded "
            "May 2022, general contractor for repair-restoration work in DNR/LNR.",
        "content_type": "text/html",
    },
    {
        "url": "https://roskapstroy.ru/firm/rks-nr/",
        "source_type": "press_article",
        "title": "RosKapStroy official page on subsidiary RKS-NR",
        "description": "Confirms RKS-NR director full name: Шарипов Ильдар Радикович "
            "(Sharipov Ildar Radikovich) -- first full ФИО w/ patronymic for this figure. "
            "Confirms RKS-NR's Mariupol office: пер. Нахимова, д. 6 -- same registered "
            "address as RKS-Development's dev_legal_addr in EISZhS data, supporting the "
            "parent/subsidiary relationship already inferred.",
        "content_type": "text/html",
    },
]

for t in targets:
    try:
        r = requests.get(t["url"], headers={"User-Agent": config.USER_AGENT}, timeout=20)
    except requests.RequestException as e:
        print("FAIL", t["url"], e)
        continue
    if r.status_code != 200:
        print("HTTP", r.status_code, t["url"])
        continue
    sha = forensics.capture_source(
        r.content, url=t["url"], source_type=t["source_type"], title=t["title"],
        description=t["description"], content_type=r.headers.get("Content-Type","text/html"),
        http_status=r.status_code, con=con,
    )
    print("captured", t["url"], "->", sha[:12])
con.close()
