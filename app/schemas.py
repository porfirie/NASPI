from pydantic import BaseModel


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
