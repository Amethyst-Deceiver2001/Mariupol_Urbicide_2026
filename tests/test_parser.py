"""Tests for the improved case-card parser."""
from mariupol_seizures.parse.case_parser import parse_case_card

# Minimal synthetic HTML modelled on a typical ГАС Правосудие case card.
SAMPLE_HTML = """
<html><body>
<h2>Дело № 2-1234/2024</h2>
<p>Судья: Иванов И.В.</p>
<p>Заявитель: Администрация города Мариуполя</p>
<p>Заинтересованное лицо: Петренко Олена Іванівна</p>
<div id="cont3"><p>
  Признать право муниципальной собственности на квартиру
  площадью 54.3 кв.м, расположенную по адресу
  ул. Казанцева, д. 7, кв. 12, г. Мариуполь.
  Кадастровый номер 14:03:0401001:5678.
  Ввиду отсутствия регистрации в ЕГРН и непоступления заявлений
  в установленный срок в соответствии с Законом ДНР 66-РЗ.
  Заявление удовлетворить.
</p></div>
<table>
  <tr><td>Поступил в суд</td><td>01.04.2024</td></tr>
  <tr><td>Решение вынесено</td><td>15.05.2024</td></tr>
  <tr><td>Вступил в законную силу</td><td>20.06.2024</td></tr>
</table>
</body></html>
"""

# Card with minimal fields — parser should degrade gracefully.
SPARSE_HTML = "<html><body><p>Дело № 2-9/2025</p></body></html>"


def test_case_number():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec["case_number"] == "2-1234/2024"


def test_judge():
    rec = parse_case_card(SAMPLE_HTML)
    assert "Иванов" in rec["judge"]


def test_petitioner():
    rec = parse_case_card(SAMPLE_HTML)
    assert "Администрация" in rec["petitioner"]


def test_owner_extracted_and_flagged_sensitive():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec.get("owner_sensitive") is True
    assert "Петренко" in rec["owner_raw"]


def test_address_extracted():
    rec = parse_case_card(SAMPLE_HTML)
    assert any("Казанцева" in a for a in rec["addresses"])


def test_cadastral_number():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec["cadastral_no"] == "14:03:0401001:5678"


def test_area():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec["area_sqm"] == "54.3"


def test_property_type():
    rec = parse_case_card(SAMPLE_HTML)
    assert "кварт" in rec["property_type"]


def test_legal_grounds():
    rec = parse_case_card(SAMPLE_HTML)
    assert "no_egrn_registration" in rec["legal_grounds"]
    assert "law_66_rz" in rec["legal_grounds"]


def test_outcome_granted():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec["outcome"] == "granted"


def test_stages_and_dates():
    rec = parse_case_card(SAMPLE_HTML)
    stages = {s["stage"] for s in rec["stages"]}
    assert "court_petition" in stages
    assert "court_transfer" in stages
    assert "entered_force" in stages
    assert rec["filed_date"] == "01.04.2024"
    assert rec["decided_date"] == "15.05.2024"
    assert rec["entered_force_date"] == "20.06.2024"


def test_rd4u_hint():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec["rd4u_category_hint"] == "A3.6"


def test_parse_confidence_full():
    rec = parse_case_card(SAMPLE_HTML)
    assert rec["parse_confidence"] >= 0.8


def test_sparse_card_degrades_gracefully():
    rec = parse_case_card(SPARSE_HTML)
    assert rec["case_number"] == "2-9/2025"
    assert "judge" not in rec
    assert "owner_raw" not in rec
    assert rec["parse_confidence"] < 0.5


def test_no_duplicate_stages():
    rec = parse_case_card(SAMPLE_HTML)
    keys = [(s["stage"], s["date"]) for s in rec["stages"]]
    assert len(keys) == len(set(keys))
