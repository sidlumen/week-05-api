import anthropic
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from agent import run_agent, tools, tool_functions
from database import engine, get_db
from models import Book, Base
from schemas import BookCreate, BookUpdate, BookResponse

# Create all tables on startup if they don't already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Tracker API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to Book Tracker API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/books", response_model=list[BookResponse])
def get_books(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Book)
    if status:
        query = query.filter(Book.status == status)
    return query.all()


@app.get("/books/stats")
def get_stats(db: Session = Depends(get_db)):
    books = db.query(Book).all()
    total = len(books)

    status_counts = {"reading": 0, "read": 0, "want_to_read": 0}
    for book in books:
        status_counts[book.status] += 1

    rated_books = [b for b in books if b.status == "read" and b.rating is not None]
    average_rating = sum(b.rating for b in rated_books) / len(rated_books) if rated_books else None

    return {"total": total, "by_status": status_counts, "average_rating": average_rating}


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(data: BookCreate, db: Session = Depends(get_db)):
    book = Book(**data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, updates: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if updates.status is not None:
        book.status = updates.status
    if updates.rating is not None:
        book.rating = updates.rating
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"message": "Book deleted"}


ai_client = anthropic.Anthropic()


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


@app.post("/ai/chat")
def chat_with_assistant(request: ChatRequest):
    messages = request.conversation_history + [
        {"role": "user", "content": request.message}
    ]

    response = ai_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""You are Marcus, a passionate and opinionated literature professor
who has strong views about books. You're enthusiastic and sometimes dramatic.""",
        messages=messages
    )

    reply = response.content[0].text

    return {
        "reply": reply,
        "updated_history": messages + [{"role": "assistant", "content": reply}]
    }


@app.post("/ai/recommend")
def get_recommendations(request: ChatRequest, db: Session = Depends(get_db)):
    # Fetch all books from the database
    books = db.query(Book).all()

    # Build a summary of the user's library
    read_books = [b for b in books if b.status == "read"]
    reading_books = [b for b in books if b.status == "reading"]

    book_context = "Here is the user's book library:\n"

    if read_books:
        book_context += "\nBooks they've read:\n"
        for b in read_books:
            rating_str = f" (rated {b.rating}/5)" if b.rating else ""
            book_context += f"- {b.title} by {b.author}{rating_str}\n"

    if reading_books:
        book_context += "\nCurrently reading:\n"
        for b in reading_books:
            book_context += f"- {b.title} by {b.author}\n"

    if not read_books and not reading_books:
        book_context += "No books tracked yet.\n"

    system_prompt = f"""You are a personalized book recommendation assistant.

{book_context}

Based on this reading history, provide thoughtful, personalized recommendations.
Be specific about why each recommendation matches their taste.
Keep responses concise — 2-3 recommendations at most unless asked for more."""

    messages = request.conversation_history + [
        {"role": "user", "content": request.message}
    ]

    response = ai_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages
    )

    reply = response.content[0].text
    return {
        "reply": reply,
        "updated_history": messages + [{"role": "assistant", "content": reply}]
    }


class AgentRequest(BaseModel):
    message: str


@app.post("/ai/agent")
def book_agent(request: AgentRequest):
    reply, agent_steps = run_agent(request.message, tools, tool_functions)
    return {"response": reply, "agent_steps": agent_steps}