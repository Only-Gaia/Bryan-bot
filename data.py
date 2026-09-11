import json
import os

DATA_DIR = "data_files"
os.makedirs(DATA_DIR, exist_ok=True)

# Nomi dei "file" di dati conosciuti dal bot.
# Nuovi nomi vengono comunque aggiunti automaticamente al primo save().
FILES = {
    "warns",
    "settings",
}


def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def load(name):
    """Carica il contenuto del file JSON `name`. Ritorna {} se non esiste."""
    FILES.add(name)
    path = _path(name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save(name, obj):
    """Salva `obj` nel file JSON `name`."""
    FILES.add(name)
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)
