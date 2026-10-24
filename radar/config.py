import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_PATH = Path(os.environ.get("RADAR_MODEL_PATH", ROOT / "models" / "radar.joblib"))
HISTORY_PATH = Path(os.environ.get("RADAR_HISTORY_PATH", DATA_DIR / "current.json"))
SOURCE = "https://www.kaggle.com/datasets/adaoduque/campeonato-brasileiro-de-futebol"
DOWNLOAD = "https://www.kaggle.com/api/v1/datasets/download/adaoduque/campeonato-brasileiro-de-futebol"
