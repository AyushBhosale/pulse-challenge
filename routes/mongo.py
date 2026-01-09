from fastapi import APIRouter, Depends
from database import get_mongo_db

router = APIRouter()
db = get_mongo_db()

