import os
from pathlib import Path
from typing import Union

try:
    from config import STORAGE_PATH
except ImportError:
    from app.config import STORAGE_PATH


def is_subpath(base: Path, target: Path) -> bool:
    try:
        base_resolved = base.resolve()
        target_resolved = target.resolve()
        return base_resolved == target_resolved or base_resolved in target_resolved.parents
    except RuntimeError:
        return False


def get_dir_size(start_path: Union[str, Path]) -> int:
    total_size = 0
    start_path = Path(start_path)
    for path in start_path.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total_size += path.stat().st_size
        except (OSError, PermissionError):
            continue
    return total_size


def get_user_path(username: str) -> Path:
    user_folder = Path(STORAGE_PATH) / username
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder


def safe_join_user_path(user_root: Union[str, Path], relative_path: str, create: bool = False) -> Path:
    user_root_path = Path(user_root).resolve()
    if relative_path is None or relative_path == "":
        target = user_root_path
    else:
        target = (user_root_path / relative_path).resolve()

    if not is_subpath(user_root_path, target):
        raise ValueError("Cale invalidă")

    if create and not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    return target
