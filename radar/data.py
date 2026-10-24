"""Importação auditável. Um ponteiro atômico ativa um snapshot imutável."""

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
import unicodedata
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from radar.config import DATA_DIR, DOWNLOAD, SOURCE

ALIASES = {"athletico-pr": "atletico-pr", "athletico paranaense": "atletico-pr"}


def team_id(name: str) -> str:
    plain = unicodedata.normalize("NFKD", str(name).strip()).encode("ascii", "ignore").decode()
    result = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return ALIASES.get(result, result)


def normalize(raw: bytes) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(io.BytesIO(raw))
    frame = frame.rename(columns={"rodata": "rodada"})
    required = [
        "ID",
        "rodada",
        "data",
        "mandante",
        "visitante",
        "mandante_Placar",
        "visitante_Placar",
        "vencedor",
    ]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(missing)}")
    if frame[required].isna().any().any():
        raise ValueError("Há registros incompletos nas colunas obrigatórias.")
    source_rows = len(frame)
    frame = frame.drop_duplicates().copy()
    duplicates = source_rows - len(frame)
    if frame["ID"].duplicated().any():
        raise ValueError("IDs duplicados com conteúdos diferentes.")
    for col in ["rodada", "mandante_Placar", "visitante_Placar"]:
        values = pd.to_numeric(frame[col], errors="raise")
        if ((values < 0) | (values % 1 != 0)).any():
            raise ValueError(f"Valor inválido em {col}.")
        frame[col] = values.astype(int)
    dates = pd.to_datetime(frame["data"], format="%d/%m/%Y", errors="raise")
    if (dates > pd.Timestamp.now().normalize()).any():
        raise ValueError("A base contém resultados com data futura.")
    home = frame["mandante"].map(team_id)
    away = frame["visitante"].map(team_id)
    if ((home == away) | home.eq("") | away.eq("")).any():
        raise ValueError("Clubes inválidos ou confronto contra o próprio clube.")
    hg, ag = frame["mandante_Placar"], frame["visitante_Placar"]
    result = pd.Series("D", index=frame.index)
    result.loc[hg > ag] = "H"
    result.loc[hg < ag] = "A"
    winners = frame["vencedor"].map(team_id)
    invalid = ((result == "H") & (winners != home)) | ((result == "A") & (winners != away))
    invalid |= (result == "D") & ~frame["vencedor"].astype(str).str.strip().isin(["-", "Empate", "empate"])
    if invalid.any():
        raise ValueError(f"Vencedor incompatível com placar: {int(invalid.sum())} registros.")
    # Exceção documentada: partidas de jan/fev de 2021 pertencem à edição de 2020.
    # Uma rodada 1 adiada para janeiro não pode iniciar uma temporada nova.
    seasons = dates.dt.year.copy()
    seasons.loc[(dates >= "2021-01-01") & (dates < "2021-03-01")] = 2020
    clean = (
        pd.DataFrame(
            {
                "id": frame["ID"].astype(str),
                "date": dates.dt.strftime("%Y-%m-%d"),
                "season": seasons,
                "round": frame["rodada"],
                "home": home,
                "away": away,
                "home_name": frame["mandante"].str.strip(),
                "away_name": frame["visitante"].str.strip(),
                "hg": hg,
                "ag": ag,
                "result": result,
            }
        )
        .sort_values(["date", "id"])
        .reset_index(drop=True)
    )
    ambiguous = clean.duplicated(["season", "home", "away"], keep=False)
    quarantined = clean.loc[ambiguous, ["id", "date", "home", "away"]].to_dict(orient="records")
    # Não adivinha qual mando está correto: exclui ambos do modelo e registra a evidência.
    clean = clean.loc[~ambiguous].reset_index(drop=True)
    if clean.empty:
        raise ValueError("Base vazia.")
    return clean, {
        "source_rows": source_rows,
        "duplicates_removed": duplicates,
        "quarantined_ambiguous_fixtures": quarantined,
        "rows": len(clean),
        "first_date": clean.date.min(),
        "last_date": clean.date.max(),
        "seasons": {str(k): int(v) for k, v in clean.groupby("season").size().items()},
    }


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def import_bytes(raw: bytes, directory: Path = DATA_DIR, origin: str = SOURCE) -> dict:
    clean, audit = normalize(raw)  # valida antes de alterar a versão ativa
    digest = hashlib.sha256(raw).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    current = directory / "current.json"
    if current.exists():
        old, _ = load_snapshot(current)
        if old["raw_sha256"] == digest:
            return old
        if audit["last_date"] < old["last_date"]:
            raise ValueError("Atualização rejeitada: data final anterior à base ativa.")
    snapshot = directory / "snapshots" / digest
    snapshot.mkdir(parents=True, exist_ok=True)
    records = clean.to_dict(orient="records")
    normalized_hash = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
    metadata = {
        **audit,
        "source": SOURCE,
        "download_origin": origin,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": digest,
        "normalized_sha256": normalized_hash,
        "schema_version": 1,
    }
    (snapshot / "source.csv").write_bytes(raw)
    atomic_json(snapshot / "snapshot.json", {"metadata": metadata, "matches": records})
    atomic_json(current, {"snapshot": f"snapshots/{digest}/snapshot.json"})
    return metadata


def load_snapshot(pointer: Path) -> tuple[dict, pd.DataFrame]:
    location = json.loads(pointer.read_text(encoding="utf-8"))["snapshot"]
    path = (pointer.parent / location).resolve()
    if not path.is_relative_to(pointer.parent.resolve()):
        raise ValueError("Ponteiro de dados fora do diretório permitido.")
    content = json.loads(path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps(content["matches"], sort_keys=True).encode()).hexdigest()
    if digest != content["metadata"]["normalized_sha256"]:
        raise ValueError("Integridade do snapshot inválida.")
    return content["metadata"], pd.DataFrame(content["matches"])


def download(version: int) -> bytes:
    with urllib.request.urlopen(f"{DOWNLOAD}?datasetVersionNumber={version}", timeout=120) as response:
        content = response.read()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if Path(name).name == "campeonato-brasileiro-full.csv"]
        if len(names) != 1:
            raise ValueError("Arquivo principal não encontrado no pacote Kaggle.")
        return archive.read(names[0])


def main():
    parser = argparse.ArgumentParser(description="Importa/atualiza a base do Kaggle com validação.")
    parser.add_argument("--file", type=Path, help="CSV local baixado da mesma base Kaggle")
    parser.add_argument("--version", type=int, help="Versão Kaggle; omitir para consultar a mais recente")
    args = parser.parse_args()
    version = args.version
    if not args.file and version is None:
        with urllib.request.urlopen(
            "https://www.kaggle.com/api/v1/datasets/list?search=campeonato-brasileiro-de-futebol", timeout=30
        ) as response:
            entries = json.load(response)
        entry = next(item for item in entries if item["ref"] == "adaoduque/campeonato-brasileiro-de-futebol")
        version = int(entry["currentVersionNumber"])
    raw = args.file.read_bytes() if args.file else download(version)
    origin = "Arquivo local da base Kaggle" if args.file else f"{DOWNLOAD}?datasetVersionNumber={version}"
    metadata = import_bytes(raw, origin=origin)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print("Dados prontos. Reinicie a API; retreinamento é feito por python -m radar.train.")


if __name__ == "__main__":
    main()
