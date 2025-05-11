from fastapi import FastAPI, Request, Form, HTTPException, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
from google import genai
import wikipediaapi
import datetime
import os

# === Load .env === #
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
DATABASE_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/wiki_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALGORITHM = "HS256"

# === Gemini Pro Setup === #
client = genai.Client(api_key=GEMINI_API_KEY)

# === DB Setup === #
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    articles = relationship("Article", back_populates="owner")

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    summary = Column(Text)
    url = Column(String)
    tags = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="articles")

Base.metadata.create_all(bind=engine)

# === FastAPI App Setup === #
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# === Utility Functions === #
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()

def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    db = SessionLocal()
    user = get_user(db, username)
    db.close()
    if user is None:
        raise HTTPException(status_code=401)
    return user

wiki = wikipediaapi.Wikipedia(language='en', user_agent='WikipediaApp/1.0')

def search_wikipedia(keyword: str):
    page = wiki.page(keyword)
    if page.exists():
        return {"title": page.title, "summary": page.summary, "url": page.fullurl}
    return None


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.3
)

prompt_template = ChatPromptTemplate.from_template(
    "You are a content classifier.\n"
    "Given the following article, generate 3–5 concise topic tags as a comma-separated list:\n\n"
    "{summary}\n\nTags:"
)

chain = prompt_template | llm | StrOutputParser()

def generate_tags(summary: str):
    return chain.invoke({"summary": summary}).strip()

# === HTML Routes === #
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = get_user(db, username)
    db.close()
    if not user or user.hashed_password != password:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    token = create_access_token({"sub": user.username})
    request.session["token"] = token
    return RedirectResponse(url="/search", status_code=302)

@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
def search_submit(request: Request, keyword: str = Form(...)):
    article = search_wikipedia(keyword)
    return templates.TemplateResponse("search.html", {"request": request, "article": article})

import asyncio
@app.post("/save")
async def save_article_form(request: Request, title: str = Form(...), summary: str = Form(...), url: str = Form(...)):
    token = request.session.get("token")
    current_user = get_current_user(token)
    db = SessionLocal()
    tags = generate_tags(summary)
    db_article = Article(title=title, summary=summary, url=url, tags=tags, owner=current_user)
    db.add(db_article)
    db.commit()
    db.close()
    await ws_manager.broadcast(f"New article saved: {title}")
    return RedirectResponse(url="/saved", status_code=302)

@app.get("/saved", response_class=HTMLResponse)
def saved_articles(request: Request):
    token = request.session.get("token")
    current_user = get_current_user(token)
    db = SessionLocal()
    articles = (
        db.query(Article)
        .filter(Article.owner == current_user)
        .order_by(Article.id.desc())      # latest first
        .limit(4)                         # only 4 articles
        .all()
    )
    db.close()
    return templates.TemplateResponse("saved.html", {"request": request, "articles": articles})



@app.post("/update-tags")
def update_tags(article_id: int = Form(...), tags: str = Form(...), request: Request = None):
    token = request.session.get("token")
    current_user = get_current_user(token)
    db = SessionLocal()
    article = db.query(Article).filter(Article.id == article_id, Article.owner == current_user).first()
    if article:
        article.tags = tags
        db.commit()
    db.close()
    return RedirectResponse(url="/saved", status_code=302)


from fastapi import WebSocket
from typing import List

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

ws_manager = WebSocketManager()


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # can be used for pings or user messages
    except Exception:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8070, reload=True)
