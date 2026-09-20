from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="Sistema de Tickets", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.allow_credentials, # Validador que impide que en allow_origins se ponga ["*"] y exponga cookies/headers
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}