from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

import db
from auth import check_pw, current_parent, hash_pw, make_token

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str


class ChildIn(BaseModel):
    name: str
    age: Optional[int] = None
    doll_id: str = "doll1"


class TopicIn(BaseModel):
    title: str
    subject: Optional[str] = None
    content: str
    active: bool = True


@router.post("/auth/register")
def register(body: Credentials):
    if db.fetch_one("SELECT id FROM parents WHERE email=%s", (body.email,)):
        raise HTTPException(409, "Email already registered")
    row = db.fetch_one(
        "INSERT INTO parents (email, password_hash) VALUES (%s,%s) RETURNING id",
        (body.email, hash_pw(body.password)))
    return {"token": make_token(row["id"])}


@router.post("/auth/login")
def login(body: Credentials):
    row = db.fetch_one("SELECT id, password_hash FROM parents WHERE email=%s", (body.email,))
    if not row or not check_pw(body.password, row["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(row["id"])}


# ---------- children ----------
@router.get("/children")
def list_children(pid: int = Depends(current_parent)):
    return db.fetch_all("SELECT * FROM children WHERE parent_id=%s ORDER BY id", (pid,))


@router.post("/children")
def add_child(body: ChildIn, pid: int = Depends(current_parent)):
    return db.fetch_one(
        "INSERT INTO children (parent_id, name, age, doll_id) VALUES (%s,%s,%s,%s) RETURNING *",
        (pid, body.name, body.age, body.doll_id))


# ---------- topics ----------
@router.get("/topics")
def list_topics(pid: int = Depends(current_parent)):
    return db.fetch_all("SELECT * FROM topics WHERE parent_id=%s ORDER BY id", (pid,))


@router.post("/topics")
def add_topic(body: TopicIn, pid: int = Depends(current_parent)):
    return db.fetch_one(
        "INSERT INTO topics (parent_id, title, subject, content, active) "
        "VALUES (%s,%s,%s,%s,%s) RETURNING *",
        (pid, body.title, body.subject, body.content, body.active))


@router.put("/topics/{topic_id}")
def update_topic(topic_id: int, body: TopicIn, pid: int = Depends(current_parent)):
    row = db.fetch_one(
        "UPDATE topics SET title=%s, subject=%s, content=%s, active=%s "
        "WHERE id=%s AND parent_id=%s RETURNING *",
        (body.title, body.subject, body.content, body.active, topic_id, pid))
    if not row:
        raise HTTPException(404, "Topic not found")
    return row


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, pid: int = Depends(current_parent)):
    row = db.fetch_one("DELETE FROM topics WHERE id=%s AND parent_id=%s RETURNING id",
                       (topic_id, pid))
    if not row:
        raise HTTPException(404, "Topic not found")
    return {"deleted": True}