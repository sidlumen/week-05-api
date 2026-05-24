from fastapi import FastAPI

app = FastAPI(title="Book Tracker API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to Book Tracker API"}

@app.get("/health")
def health():
    return {"status": "ok"}
