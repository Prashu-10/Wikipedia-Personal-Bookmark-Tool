# Wikipedia-Personal-Bookmark-Tool
web app to search Wikipedia, save articles with AI-generated tags using Gemini Pro (via LangChain), and view or update saved content — all with login, real-time updates, and session-based UI.

---

## ✨ Features

- 🔍 Search Wikipedia articles  
- 💾 Save articles to user account  
- 🏷️ Auto-generate tags using Gemini Pro (LangChain)  
- 🔐 JWT-based login via HTML form  
- 🖼️ Jinja2 template UI (responsive + styled)  
- 📡 WebSocket real-time notifications  
- 📄 Pagination backend ready  
- 🛠️ Compatible with PostgreSQL & CockroachDB  

---

## 🔧 Tech Stack

- **Backend:** FastAPI + SQLAlchemy  
- **Frontend:** Jinja2 templates (pure HTML/CSS)  
- **AI Tags:** Gemini Pro via LangChain  
- **Database:** PostgreSQL / CockroachDB  
- **Live Updates:** WebSocket  

---

## 📦 Local Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/wiki-bookmark-app.git
cd wiki-bookmark-app
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv wiki-env
source wiki-env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> If `requirements.txt` is missing, use:

```txt
fastapi
uvicorn
sqlalchemy
jinja2
python-jose
python-dotenv
wikipedia-api
requests
itsdangerous
langchain
langchain-google-genai
psycopg2-binary
beautifulsoup4
```

---

## 🛠️ Database Setup (PostgreSQL)

### macOS (via Homebrew)

```bash
brew install postgresql
brew services start postgresql
```

### Create DB & User

```bash
psql postgres
```

Then run:

```sql
CREATE USER wiki_user WITH PASSWORD 'admin';
CREATE DATABASE wiki_db OWNER wiki_user;
```

---

## 🔐 Admin Credentials

| Username | Password |
|----------|----------|
| admin    | admin    |

If needed, insert manually into the database:

```sql
INSERT INTO users (username, hashed_password) VALUES ('admin', 'admin');
```

---

## 📄 .env File

Create a `.env` in the project root with:

```env
SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-google-genai-api-key
DB_URL=postgresql+psycopg2://wiki_user:admin@localhost:5432/wiki_db
```

---

## 🚀 Run the Application

```bash
python main.py
```

Then open your browser at:

```
http://127.0.0.1:8070
```

---

## 📡 WebSocket Notification

Real-time alerts will appear when new articles are saved:

```text
New article saved: Artificial Intelligence
```

This is handled via `ws://localhost:8070/ws/updates`.

---

## 📁 Folder Structure

```
project/
├── main.py
├── templates/
│   ├── login.html
│   ├── search.html
│   └── saved.html
├── static/
│   └── style.css
├── .env
├── requirements.txt
```

---

