"""Tests for the address normalizer / toponym lookup."""
from pathlib import Path

from mariupol_seizures.normalize import toponym as tp


def _seed(tmp_path: Path, rows: str) -> Path:
    """Write a temporary toponyms CSV and return its path."""
    p = tmp_path / "toponyms.csv"
    header = (
        "prewar_name,occupation_name,kind,changed_on,"
        "source_ref,notes\n"
    )
    p.write_text(header + rows, encoding="utf-8")
    return p


def _reset_cache() -> None:
    tp.load_toponyms.cache_clear()


def test_key_strips_leading_prefix():
    # Russian and Ukrainian street prefixes both recognised.
    assert tp._key("ул. Артёма") == tp._key("вул. Артема")
    assert tp._key("проспект Ленина") == tp._key("пр. Ленина")


def test_key_strips_trailing_prefix():
    # "Тульский проспект" form (prefix is the suffix).
    assert tp._key("Тульский проспект") == tp._key("проспект Тульский")


def test_key_folds_yo_and_ye():
    # ё ↔ е and ї ↔ и and і ↔ и all fold for matching only.
    assert tp._key("ул. Артёма") == tp._key("ул. Артема")
    assert tp._key("просп. Леніна") == tp._key("просп. Ленина")


def test_key_preserves_soft_sign():
    # _key() (building_key grouping) keeps ь -- it's part of the correct
    # spelling for streets like "Азовстальская"/"Львовская", and dropping
    # it there would corrupt building_key.
    assert tp._key("ул. Азовстальская") == "STREET:азовстальская"
    assert tp._key("ул. Львовская") == "STREET:львовская"


def test_toponym_match_key_drops_soft_sign():
    # _toponym_match_key() (data/toponyms.csv lookups only) folds ь away:
    # UA "Тульський" and RU "Тульский" differ only by ь, same for UA
    # "Дзержинського" vs RU "Дзержинского", and OCR'd RU forms that drop ь
    # (e.g. "Энгелса" for "Энгельса").
    assert tp._toponym_match_key("Тульский проспект") == tp._toponym_match_key("Тульський проспект")
    assert tp._toponym_match_key("ул. Дзержинского") == tp._toponym_match_key("вул. Дзержинського")
    assert tp._toponym_match_key("ул. Энгелса") == tp._toponym_match_key("ул. Энгельса")


def test_key_preserves_street_class():
    # CRITICAL: a square and an avenue with the same proper-name MUST NOT
    # collide. Two different physical objects.
    assert tp._key("просп. Леніна") != tp._key("Площа Леніна")
    assert tp._key("ул. Артема") != tp._key("пер. Артема")


def test_zhms_azovsky_variants_fold_to_microdistrict():
    # "ЖМС Азовский" (registry XLSX, leading abbrev), "Азовский жилмассив"
    # (official ua-region.com.ua form, trailing), "жилмасив Азовский"
    # (damage_assessment, 1-c spelling, leading) and "жилмассив Азовский"
    # (minstroy, 2-c spelling, leading) all name the same residential
    # complex and must collapse to one MICRODISTRICT building_key namespace.
    assert tp._key("ЖМС Азовский") == "MICRODISTRICT:азовский"
    assert tp._key("Азовский жилмассив") == "MICRODISTRICT:азовский"
    assert tp._key("жилмасив Азовский") == "MICRODISTRICT:азовский"
    assert tp._key("жилмассив Азовский") == "MICRODISTRICT:азовский"


def test_unprefixed_does_not_match_prefixed():
    # Inputs without a recognised class word fall into CLASS_UNKNOWN and
    # MUST NOT match real prefixed entries — better to miss than misattribute.
    assert tp._key("Артема") != tp._key("ул. Артема")


def test_exact_match_returns_prewar(tmp_path):
    csv_path = _seed(
        tmp_path,
        "вул. Митрополитська,ул. Артёма,rename,2022-04-22,"
        "https://example.org/decree,test seed\n",
    )
    _reset_cache()
    result = tp.normalize_address(
        "ул. Артёма, д. 7, кв. 12", path=str(csv_path)
    )
    assert result["prewar_name"] == "вул. Митрополитська"
    assert result["toponym_confidence"] == 1.0
    assert result["toponym_source"].startswith("http")


def test_unknown_street_returns_none(tmp_path):
    csv_path = _seed(tmp_path, "")
    _reset_cache()
    result = tp.normalize_address(
        "ул. Несуществующая, д. 1", path=str(csv_path)
    )
    assert result["prewar_name"] is None
    assert result["toponym_confidence"] == 0.0
    assert result["occupation_address"] == "ул. Несуществующая, д. 1"


def test_rows_without_source_are_skipped(tmp_path):
    # No source_ref means the row is forensic-data-unsafe and must be skipped.
    csv_path = _seed(
        tmp_path,
        "вул. Тест,ул. Тестовая,rename,2022,,no source\n",
    )
    _reset_cache()
    index = tp.load_toponyms(str(csv_path))
    assert index == {}


def test_comment_lines_are_skipped(tmp_path):
    csv_path = _seed(
        tmp_path,
        "# this is a comment row\n"
        "вул. Реальна,ул. Реальная,rename,2022,https://x.test,\n",
    )
    _reset_cache()
    index = tp.load_toponyms(str(csv_path))
    assert len(index) == 1


def test_missing_csv_returns_empty(tmp_path):
    _reset_cache()
    missing = tmp_path / "nope.csv"
    assert tp.load_toponyms(str(missing)) == {}


def test_empty_input_safe():
    _reset_cache()
    result = tp.normalize_address("")
    assert result["prewar_name"] is None
    assert result["occupation_address"] == ""
