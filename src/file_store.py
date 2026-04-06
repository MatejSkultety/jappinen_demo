from pathlib import Path

from .config import UPLOADS_DIR


def ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def list_uploaded_files() -> list[str]:
    ensure_uploads_dir()
    return sorted(path.name for path in UPLOADS_DIR.glob("*.xlsx") if path.is_file())


def save_uploaded_file(uploaded_file) -> Path:
    ensure_uploads_dir()
    filename = Path(uploaded_file.name).name
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("Only .xlsx files are supported.")

    target_path = UPLOADS_DIR / filename
    with target_path.open("wb") as target_file:
        target_file.write(uploaded_file.getbuffer())
    return target_path


def delete_uploaded_file(filename: str) -> None:
    file_path = UPLOADS_DIR / Path(filename).name
    if file_path.exists():
        file_path.unlink()