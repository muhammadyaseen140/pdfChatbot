"""SQLite persistence layer: user accounts, password-reset codes and chat history."""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager

import bcrypt

DB_FILE = os.getenv("APP_DB_FILE", "app_data.db")
RESET_CODE_TTL_SECONDS = 15 * 60
MAX_RESET_ATTEMPTS = 5
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@contextmanager
def get_connection():
    """Yield a SQLite connection that commits on success and always closes."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create all tables if they do not exist yet."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash BLOB NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reset_codes (
                email TEXT PRIMARY KEY,
                code_hash TEXT NOT NULL,
                expires_at REAL NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                messages TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )


# ---------------------------------------------------------------- validation
def normalize_email(email):
    """Lower-case and strip an email address."""
    return (email or "").strip().lower()


def validate_email(email):
    """Return an error message if the email is invalid, otherwise None."""
    if not EMAIL_PATTERN.match(normalize_email(email)):
        return "Please enter a valid email address."
    return None


def validate_password(password):
    """Return an error message if the password is too weak, otherwise None."""
    if len(password or "") < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return None


def _hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


# ---------------------------------------------------------------------- users
def create_user(name, email, password):
    """Create a new account. Returns (success, message)."""
    name = (name or "").strip()
    email = normalize_email(email)
    if len(name) < 2:
        return False, "Please enter your full name."
    error = validate_email(email) or validate_password(password)
    if error:
        return False, error
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, email, _hash_password(password), time.time()),
            )
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    return True, "Account created successfully."


def authenticate_user(email, password):
    """Return a user dict if credentials are valid, otherwise None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (normalize_email(email),),
        ).fetchone()
    if row and bcrypt.checkpw((password or "").encode("utf-8"), row["password_hash"]):
        return {"id": row["id"], "name": row["name"], "email": row["email"]}
    return None


# ------------------------------------------------------------ password reset
def _hash_code(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_reset_code(email):
    """Generate a 6-digit reset code for an existing user, or return None."""
    email = normalize_email(email)
    with get_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return None
        code = f"{secrets.randbelow(10**6):06d}"
        conn.execute(
            "INSERT OR REPLACE INTO reset_codes (email, code_hash, expires_at, attempts) "
            "VALUES (?, ?, ?, 0)",
            (email, _hash_code(code), time.time() + RESET_CODE_TTL_SECONDS),
        )
    return code


def reset_password(email, code, new_password):
    """Set a new password if the reset code is valid. Returns (success, message)."""
    email = normalize_email(email)
    error = validate_password(new_password)
    if error:
        return False, error
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM reset_codes WHERE email = ?", (email,)).fetchone()
        if not row or row["expires_at"] < time.time() or row["attempts"] >= MAX_RESET_ATTEMPTS:
            return False, "The code is invalid or has expired. Please request a new one."
        if not hmac.compare_digest(row["code_hash"], _hash_code((code or "").strip())):
            conn.execute("UPDATE reset_codes SET attempts = attempts + 1 WHERE email = ?", (email,))
            return False, "The code is incorrect."
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (_hash_password(new_password), email),
        )
        conn.execute("DELETE FROM reset_codes WHERE email = ?", (email,))
    return True, "Password updated. You can sign in now."


# ---------------------------------------------------------------------- chats
def save_chat(user_id, chat_id, title, messages):
    """Insert or update a chat for the given user."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chats (id, user_id, title, messages, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET messages = excluded.messages, updated_at = excluded.updated_at "
            "WHERE chats.user_id = excluded.user_id",
            (chat_id, user_id, title, json.dumps(messages), time.time()),
        )


def get_chat_history(user_id):
    """Return all chats of a user (id, title, messages) in the order they were created."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, messages FROM chats WHERE user_id = ? ORDER BY rowid",
            (user_id,),
        ).fetchall()
    return [{"id": r["id"], "title": r["title"], "messages": json.loads(r["messages"])} for r in rows]
