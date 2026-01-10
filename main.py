from fastapi import FastAPI
# from routes.rdbms import router as rdbms_router
# from mongo import router as mongo_router
from routes.video import router as video_router
from routes.auth import router as auth_router

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(video_router, prefix="/video", tags=["video"])
@app.get("/")
async def root():
    return {"message": "Hello World"}


