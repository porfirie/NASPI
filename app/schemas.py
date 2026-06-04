from pydantic import BaseModel
from typing import List

class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class UsernameChange(BaseModel):
    new_username: str


class UserEdit(BaseModel):
    role: str
    storage_quota_mb: int


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"
    storage_quota_mb: int = 5000


class FolderCreate(BaseModel):
    path: str
    folder_name: str

class MoveRequest(BaseModel):
    source_paths: List[str]
    destination_folder: str

class CopyFilesRequest(BaseModel):
    source_paths: List[str]
    destination_folder: str

class DeleteMultipleRequest(BaseModel):
    filenames: List[str]

class RenameFolderRequest(BaseModel):
    folder_path: str
    new_name: str

class AIControlRequest(BaseModel):
    action: str
