import os
from pathlib import Path
from typing import Union
import hashlib



try:
    from config import STORAGE_PATH
    from app.models import User
except ImportError:
    from app.config import STORAGE_PATH
    from app.models import User


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


def get_user_path(user_id: int) -> Path:
    # Acum folderul va fi creat pe baza ID-ului (ex: storage/1)
    user_folder = Path(STORAGE_PATH) / str(user_id)
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

def _calculate_storage_stats(current_user: User, user_root: Path) -> dict:
    user_quota_mb = current_user.storage_quota_mb
    used_mb = get_dir_size(user_root) / (1024 * 1024)
    free_mb = max(0, user_quota_mb - used_mb)
    percent_used = (used_mb / user_quota_mb) * 100 if user_quota_mb > 0 else 100

    return {
        "total_gb": round(user_quota_mb / 1024, 2),
        "used_gb": round(used_mb / 1024, 2),
        "free_gb": round(free_mb / 1024, 2),
        "app_usage_mb": round(used_mb, 2),
        "percent_used": round(percent_used, 1),
        "user_role": current_user.role
    }

def get_temp_file_path(user_root: Path, target_path: str, filename: str) -> Path:
    """
    Creează un nume unic și sigur pentru fișierul temporar.
    Folosim MD5 ca să nu se încurce dacă urci două fișiere cu același nume în foldere diferite.
    """
    temp_dir = user_root / ".temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    unique_string = f"{target_path}/{filename}".encode()
    unique_name = hashlib.md5(unique_string).hexdigest()
    
    return temp_dir / f"{unique_name}.part"