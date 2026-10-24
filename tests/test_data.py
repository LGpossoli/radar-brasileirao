import io
import json

import pandas as pd
import pytest

from radar.data import import_bytes, load_snapshot, normalize, team_id
from tests.conftest import csv_edit


def test_season_2020_extends_into_2021(clean):
    assert clean.loc[clean.id.eq("3"), "season"].item() == 2020
    assert clean.loc[clean.id.eq("4"), "season"].item() == 2021


def test_names_and_aliases():
    assert team_id(" São Paulo ") == "sao-paulo"
    assert team_id("Athletico-PR") == team_id("Atletico-PR")


@pytest.mark.parametrize(
    "changes",
    [{"mandante_Placar": -1}, {"vencedor": "Santos"}, {"mandante": "Palmeiras"}, {"data": "31/02/2020"}],
)
def test_invalid_rows_rejected(raw_csv, changes):
    with pytest.raises((ValueError, TypeError)):
        normalize(csv_edit(raw_csv, **changes))


def test_exact_duplicates_removed(raw_csv):
    frame = pd.read_csv(io.BytesIO(raw_csv))
    doubled = pd.concat([frame, frame.iloc[[0]]]).to_csv(index=False).encode()
    clean, audit = normalize(doubled)
    assert len(clean) == 4
    assert audit["duplicates_removed"] == 1


def test_ambiguous_fixtures_quarantined(raw_csv):
    frame = pd.read_csv(io.BytesIO(raw_csv))
    another = frame.iloc[[0]].copy()
    another["ID"] = 99
    another["data"] = "05/08/2020"
    clean, audit = normalize(pd.concat([frame, another]).to_csv(index=False).encode())
    assert len(clean) == 3
    assert len(audit["quarantined_ambiguous_fixtures"]) == 2


def test_failed_update_and_repeat_preserve_snapshot(tmp_path, raw_csv):
    first = import_bytes(raw_csv, tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    second = import_bytes(raw_csv, tmp_path)
    assert first == second
    with pytest.raises(ValueError):
        import_bytes(csv_edit(raw_csv, vencedor="Santos"), tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    meta, frame = load_snapshot(tmp_path / "current.json")
    assert meta == first and len(frame) == 4


def test_tampered_snapshot_rejected(tmp_path, raw_csv):
    import_bytes(raw_csv, tmp_path)
    pointer = tmp_path / "current.json"
    path = tmp_path / json.loads(pointer.read_text())["snapshot"]
    content = json.loads(path.read_text())
    content["matches"][0]["hg"] = 9
    path.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="Integridade"):
        load_snapshot(pointer)
