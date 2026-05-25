from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Book Tracker API", version="1.0.0")


# Pydantic models for validation
class BookCreate(BaseModel):
    title: str
    author: str
    status: str = "want_to_read"  # "reading", "read", "want_to_read"
    rating: Optional[int] = None  # 1-5, only if status is "read"


class BookUpdate(BaseModel):
    status: Optional[str] = None
    rating: Optional[int] = None


# In-memory storage
books_db = []
next_id = 1


@app.get("/")
def read_root():
    return {"message": "Welcome to Book Tracker API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/books")
def get_books(status: Optional[str] = None):
    if status:
        return [b for b in books_db if b["status"] == status]
    return books_db


@app.get("/books/stats")
def get_stats():
    total = len(books_db)

    status_counts = {"reading": 0, "read": 0, "want_to_read": 0}
    for book in books_db:
        status_counts[book["status"]] += 1

    rated_books = [b for b in books_db if b["status"] == "read" and b["rating"] is not None]
    if rated_books:
        average_rating = sum(b["rating"] for b in rated_books) / len(rated_books)
    else:
        average_rating = None

    return {
        "total": total,
        "by_status": status_counts,
        "average_rating": average_rating,
    }


@app.get("/books/{book_id}")
def get_book(book_id: int):
    for book in books_db:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    global next_id
    new_book = book.model_dump()
    new_book["id"] = next_id
    books_db.append(new_book)
    next_id += 1
    return new_book


@app.put("/books/{book_id}")
def update_book(book_id: int, updates: BookUpdate):
    for book in books_db:
        if book["id"] == book_id:
            if updates.status is not None:
                book["status"] = updates.status
            if updates.rating is not None:
                book["rating"] = updates.rating
            return book
    raise HTTPException(status_code=404, detail="Book not found")


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    for book in books_db:
        if book["id"] == book_id:
            books_db.remove(book)
            return {"message": "Book deleted"}
    raise HTTPException(status_code=404, detail="Book not found")
