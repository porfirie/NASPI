import sys
import os

# Ne asigurăm că Python se uită în folderul curent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from models import User  # Importăm DIRECT clasa User, nu tot modulul
import auth

def create_initial_user():
    try:
        print("--- Verificare tabele... ---")
        Base.metadata.create_all(bind=engine)
        
        db = SessionLocal()
        username = "admin"
        password = "admin123" 

        # Acum folosim User direct, fără "models." în față
        existing_user = db.query(User).filter(User.username == username).first()
        
        if existing_user:
            print(f"Utilizatorul '{username}' există deja.")
            return

        hashed_pwd = auth.get_password_hash(password) 

        new_user = User(
            username=username,
            hashed_password=hashed_pwd,
            role="admin"
        )

        db.add(new_user)
        db.commit()
        print(f"SUCCES! Utilizatorul '{username}' a fost creat.")
    
    except Exception as e:
        print(f"EROARE: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_user()