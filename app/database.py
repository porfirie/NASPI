from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

try:
    from config import DATABASE_URL
except ImportError:
    from app.config import DATABASE_URL

SQLALCHEMY_DATABASE_URL = DATABASE_URL

# 2. Creăm motorul de conexiune (Engine)
# 'check_same_thread': False este specific pentru SQLite ca să meargă cu FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Creăm o fabrică de sesiuni (pentru a interoga baza de date)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Aceasta este clasa mamă din care vor moșteni toate tabelele noastre
Base = declarative_base()

# Funcție utilă pentru a obține o conexiune temporară
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()