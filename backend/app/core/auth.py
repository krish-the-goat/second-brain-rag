import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "1440"))
JWT_ALGORITHM = "HS256"

_BM25_DATA_DIR = os.getenv("BM25_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "auth_data"))
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", os.path.join(os.path.abspath(_BM25_DATA_DIR), "users.db"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

class UserStore:
    def __init__(self):
        os.makedirs(os.path.dirname(AUTH_DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(AUTH_DB_PATH, check_same_thread=False, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()
        self._lock = threading.Lock()

    def create_user(self, email: str, password: str) -> int:
        hashed = pwd_context.hash(password)
        with self._lock:
            try:
                cursor = self.conn.execute(
                    "INSERT INTO users (email, hashed_password, created_at) VALUES (?, ?, ?)",
                    (email, hashed, datetime.now(timezone.utc).isoformat())
                )
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                raise ValueError("Email already registered")

    def authenticate(self, email: str, password: str):
        with self._lock:
            cursor = self.conn.execute("SELECT id, hashed_password FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
        if not row:
            return None
        if not pwd_context.verify(password, row[1]):
            return None
        return row[0]

_user_store = None
def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store

def create_access_token(user_id: int) -> str:
    if not JWT_SECRET or JWT_SECRET in ("", "change-me"):
        raise RuntimeError("JWT_SECRET is not configured. Set a strong secret in .env")
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        return user_id
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
