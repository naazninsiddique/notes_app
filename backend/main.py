# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, constr
from typing import List
from datetime import datetime

# SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# Password hashing
from passlib.context import CryptContext

# JWT
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException

# optional: load secret from .env
from dotenv import load_dotenv
import os
load_dotenv()

# ------------ CONFIG -------------
DATABASE_URL = "sqlite:///./notes.db"
SECRET = os.getenv("AUTHJWT_SECRET_KEY", "change_this_to_a_strong_secret")

# ------------ DB setup ------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ------------ PASSWORD UTILS ------------
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(p: str):
    return pwd_ctx.hash(p)
def verify_password(plain: str, hashed: str):
    return pwd_ctx.verify(plain, hashed)

# ------------ MODELS ------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    notes = relationship("NoteDB", back_populates="owner")

class NoteDB(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="notes")

Base.metadata.create_all(bind=engine)

# ------------ Pydantic Schemas ------------
class Settings(BaseModel):
    authjwt_secret_key: str = SECRET

@AuthJWT.load_config
def get_config():
    return Settings()

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=6)

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    class Config:
        orm_mode = True

class NoteIn(BaseModel):
    title: constr(min_length=1)
    content: constr(min_length=1)

class NoteOut(NoteIn):
    id: int
    user_id: int
    created_at: datetime
    class Config:
        orm_mode = True

# ------------ App & CORS ------------
app = FastAPI(title="Notes App (FastAPI + JWT)")

# allow React dev server origin
origins = [
    "https://notes-app-umber-mu.vercel.app/",  # exact frontend URL
    "http://localhost:3000"  # optional, dev testing
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------ Helpers ------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------ Exception handler for auth errors ------------
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request, exc):
    raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ------------ AUTH endpoints ------------
@app.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    new = User(email=user.email, password_hash=hash_password(user.password))
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@app.post("/auth/login")
def login(user: UserCreate, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Bad email or password")
    # create access token with subject = user email
    access_token = Authorize.create_access_token(subject=db_user.email)
    return {"access_token": access_token, "token_type": "bearer"}

# ------------ NOTES endpoints (protected) ------------
@app.post("/notes/", response_model=NoteOut)
def create_note(note: NoteIn, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    current_email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == current_email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid user")
    db_note = NoteDB(title=note.title, content=note.content, user_id=user.id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@app.get("/notes/", response_model=List[NoteOut])
def get_notes(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    current_email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == current_email).first()
    notes = db.query(NoteDB).filter(NoteDB.user_id == user.id).all()
    return notes

@app.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    current_email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == current_email).first()
    note = db.query(NoteDB).filter(NoteDB.id == note_id, NoteDB.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    current_email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == current_email).first()
    note = db.query(NoteDB).filter(NoteDB.id == note_id, NoteDB.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or you are not owner")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully"}
