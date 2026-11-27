import os
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

load_dotenv()

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1, max_size=5, open=False,
    kwargs={"row_factory": dict_row, "prepare_threshold": None},
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS parents (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS children (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  parent_id BIGINT REFERENCES parents(id), name TEXT NOT NULL, age INT, doll_id TEXT);
CREATE TABLE IF NOT EXISTS topics (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  parent_id BIGINT REFERENCES parents(id), title TEXT NOT NULL, subject TEXT,
  content TEXT, active BOOLEAN DEFAULT true);
CREATE TABLE IF NOT EXISTS sessions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  child_id BIGINT REFERENCES children(id), topic_id BIGINT REFERENCES topics(id),
  started_at TIMESTAMPTZ DEFAULT now(), ended_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS messages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id BIGINT REFERENCES sessions(id), role TEXT NOT NULL,
  text TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS attempts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id BIGINT REFERENCES sessions(id), topic_id BIGINT REFERENCES topics(id),
  question TEXT, child_answer TEXT, is_correct BOOLEAN, difficulty INT,
  created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doll_id TEXT, type TEXT, detail TEXT, created_at TIMESTAMPTZ DEFAULT now());

ALTER TABLE parents  ENABLE ROW LEVEL SECURITY;
ALTER TABLE children ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics   ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE events   ENABLE ROW LEVEL SECURITY;
"""

def init_db():
    pool.open()
    with pool.connection() as conn:
        conn.execute(SCHEMA)

def log_event(doll_id, type_, detail=""):
    with pool.connection() as conn:
        conn.execute("INSERT INTO events (doll_id, type, detail) VALUES (%s,%s,%s)",
                     (doll_id, type_, detail))

def fetch_all(sql, params=()):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchall()
      
def fetch_one(sql, params=()):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchone()

def execute(sql, params=()):
    with pool.connection() as conn:
        conn.execute(sql, params)