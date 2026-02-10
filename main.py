# main.py - ПОЛНАЯ ОБНОВЛЕННАЯ ВЕРСИЯ
import os
from typing import List
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, Session, SQLModel, create_engine, select, Column
from sqlalchemy import JSON  # Импортируем JSON из sqlalchemy для работы с SQLite

# --- 1. МОДЕЛЬ ДАННЫХ С ТЕГАМИ ---
class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author: str
    # Важное изменение: используем Column(JSON) для хранения списка в SQLite
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))

# Берем URL БД из переменной окружения, если нет — используем SQLite для совместимости
database_url = os.getenv("DATABASE_URL", "sqlite:///database.db")

# Важно: для PostgreSQL нужно заменить протокол postgres:// на postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(database_url, echo=True)

# --- 3. ФУНКЦИЯ ДЛЯ ЗАПОЛНЕНИЯ БАЗЫ СТАРТОВЫМИ ДАННЫМИ ---
def create_db_and_tables():
    """Создает таблицы и добавляет начальные данные, если база пуста"""
    # Создаем все таблицы из моделей SQLModel
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Проверяем, есть ли уже книги в базе
        existing_books = session.exec(select(Book)).first()
        
        # Если книг нет - добавляем стартовый набор
        if not existing_books:
            initial_books = [
                Book(
                    title="Изучаем Python", 
                    author="Марк Лутц",
                    tags=["мотивация", "учеба", "развитие", "практика"]
                ),
                Book(
                    title="Чистый код", 
                    author="Роберт Мартин",
                    tags=["профессионализм", "качество", "структура", "лучшие практики"]
                ),
                Book(
                    title="Автостопом по галактике", 
                    author="Дуглас Адамс",
                    tags=["юмор", "приключения", "философия", "абсурд"]
                ),
                Book(
                    title="1984", 
                    author="Джордж Оруэлл",
                    tags=["антиутопия", "политика", "контроль", "размышления"]
                ),
                Book(
                    title="Мастер и Маргарита", 
                    author="Михаил Булгаков",
                    tags=["мистика", "сатира", "добро и зло", "классика"]
                ),
                Book(
                    title="Три товарища", 
                    author="Эрих Мария Ремарк",
                    tags=["дружба", "любовь", "потеря", "меланхолия"]
                ),
                Book(
                    title="Маленький принц", 
                    author="Антуан де Сент-Экзюпери",
                    tags=["философия", "дети", "дружба", "простые истины"]
                ),
            ]
            
            for book in initial_books:
                session.add(book)
            session.commit()
            print("✅ База данных создана и заполнена стартовыми книгами!")

# --- 4. ВЫЗЫВАЕМ ФУНКЦИЮ СОЗДАНИЯ БАЗЫ ---
create_db_and_tables()

# --- 5. СОЗДАЕМ ПРИЛОЖЕНИЕ И ШАБЛОНЫ ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- 6. ФУНКЦИЯ РЕКОМЕНДАЦИИ (упрощенная версия) ---
def recommend_book_simple(user_query: str, all_books: List[Book]) -> Book | None:
    """Простой рекомендатель по ключевым словам"""
    if not user_query or not user_query.strip():
        return None
        
    query_words = user_query.lower().split()
    best_book = None
    best_match_score = 0
    
    for book in all_books:
        if not book.tags:
            continue
            
        # Объединяем все теги в одну строку для поиска
        tags_text = " ".join(book.tags).lower()
        match_score = sum(1 for word in query_words if word in tags_text)
        
        if match_score > best_match_score:
            best_match_score = match_score
            best_book = book
    
    return best_book

# --- 7. ЭНДПОИНТЫ ---

# Главная страница с библиотекой
@app.get("/library", response_class=HTMLResponse)
async def read_books_html(request: Request):
    with Session(engine) as session:
        books = session.exec(select(Book)).all()
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "books": books}
        )

# Обработка формы добавления книги
@app.post("/")
async def create_book_via_form(
    title: str = Form(...), 
    author: str = Form(...),
    tags: str = Form("")  # Новый параметр для тегов
):
    # Преобразуем строку тегов "приключения, мотивация" в список ["приключения", "мотивация"]
    tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    new_book = Book(title=title, author=author, tags=tags_list)
    
    with Session(engine) as session:
        session.add(new_book)
        session.commit()
        session.refresh(new_book)
    
    return RedirectResponse(url="/library", status_code=303)

# Обработка запроса на рекомендацию
@app.post("/recommend", response_class=HTMLResponse)
async def get_recommendation(request: Request, user_query: str = Form("")):
    with Session(engine) as session:
        all_books = session.exec(select(Book)).all()
        recommended_book = recommend_book_simple(user_query, all_books)
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "books": all_books,
                "recommended_book": recommended_book,
                "user_query": user_query
            }
        )

# API эндпоинты (оставляем для совместимости)
@app.get("/")
async def read_root():
    return RedirectResponse(url="/library")

@app.get("/books")
def read_books():
    with Session(engine) as session:
        return session.exec(select(Book)).all()

@app.post("/books")
def create_book(book: Book):
    with Session(engine) as session:
        session.add(book)
        session.commit()
        session.refresh(book)
        return book