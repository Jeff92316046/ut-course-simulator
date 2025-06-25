from fastapi import FastAPI
from core.config import settings
from api.router import api_router
import bcrypt

if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (object,), {"__version__": bcrypt.__version__})

app = FastAPI(
    title="ut-course-simulator",
    version="0.1.0",
    description="A robust backend API using FastAPI and SQLModel.",
    docs_url="/docs" if settings.APP_MODE != "prod" else None,
    redoc_url="/redoc" if settings.APP_MODE != "prod" else None,
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to the ut-course-simulator application!"}
