from fastapi import FastAPI
# from routes.rdbms import router as rdbms_router
# from mongo import router as mongo_router
from routes.video import router as video_router
from routes.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
load_dotenv()
origins = [os.getenv("FRONTEND_URL")]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(video_router, prefix="/video", tags=["video"])


@app.get("/")
async def root():
    return {"message": "Hello World"}


