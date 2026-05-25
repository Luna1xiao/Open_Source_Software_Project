from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
