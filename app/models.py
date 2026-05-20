from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
try:
    from database import Base
except ImportError:
    from app.database import Base
from datetime import datetime # Am păstrat doar importul corect

class FileIndex(Base):
    __tablename__ = "file_index"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    folder_path = Column(String, index=True) # va fi gol "" pentru root, sau "Excursie/Munte"
    size_kb = Column(Float)
    upload_date = Column(DateTime, default=datetime.utcnow)
    
    # Aici va scrie AI-ul cuvintele cheie (ex: "câine, munte, zăpadă")
    ai_tags = Column(String, default="") 
    
    owner_id = Column(Integer, ForeignKey("users.id"))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # admin sau user
    
    # --- NOU: Limita de stocare în Megabytes (Default 5000 MB = ~5GB) ---
    storage_quota_mb = Column(Integer, default=5000) 

class SharedFile(Base):
    __tablename__ = "shared_files"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id")) # Cel care dă share
    shared_with_id = Column(Integer, ForeignKey("users.id")) # Cel care primește
    file_path = Column(String) # Calea către fișier (ex: vacanta/poza.jpg)
    filename = Column(String)
    expires_at = Column(DateTime, nullable=True) # Când expiră share-ul
    created_at = Column(DateTime, default=datetime.utcnow)