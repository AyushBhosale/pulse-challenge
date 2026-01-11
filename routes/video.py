import os
import uuid
from typing import List
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, status
from google.cloud import storage, videointelligence
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import io
import datetime
import asyncio
import random
from fastapi import WebSocket, WebSocketDisconnect
from routes.auth import get_current_user

load_dotenv()
router = APIRouter()
SHARED_DATA = {"value": 0}

# --- Configuration ---
BUCKET_NAME = os.getenv("BUCKET_NAME")
MONGO_URI = os.getenv("MONGODB_URL")

db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["pulse_db"]
storage_client = storage.Client()
video_client = videointelligence.VideoIntelligenceServiceClient()

# --- Helpers ---

def delete_gcs_video(gcs_uri: str) -> bool:
    """Deletes a file from GCS based on its gs:// URI."""
    try:
        parsed_url = urlparse(gcs_uri)
        bucket_name = parsed_url.netloc
        blob_name = parsed_url.path.lstrip("/")

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        return True
    except Exception as e:
        print(f"Error deleting GCS object: {e}")
        return False

def check_video_content(gcs_uri: str) -> bool:
    """Uses GCP Video Intelligence to check for explicit content."""
    features = [videointelligence.Feature.EXPLICIT_CONTENT_DETECTION]
    operation = video_client.annotate_video(input_uri=gcs_uri, features=features)
    result = operation.result(timeout=180)

    # Check for explicit frames
    for frame in result.annotation_results[0].explicit_annotation.frames:
        if frame.pornography_likelihood >= videointelligence.Likelihood.LIKELY:
            return True
    return False

# --- Routes ---

@router.post("/upload-video/")
async def upload_and_process_video(
    description: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("username")
    SHARED_DATA[username] = "Uploading to GCS"
    # 1. Upload to GCS
    try:
        # Generate a unique filename to prevent overwrites
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(unique_filename)
        
        blob.upload_from_file(file.file, content_type=file.content_type)
        video_url = f"gs://{BUCKET_NAME}/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS Upload Failed: {str(e)}")
    SHARED_DATA[username] = "Content Flagging"
    # 2. Content Flagging
    is_flagged = check_video_content(video_url)
    SHARED_DATA[username] = "Storing Metadata"
    # 3. Store Metadata
    video_record = {
        "username": username,
        "description": description,
        "video_url": video_url,
        "is_flagged": is_flagged,
    }
    
    await db["videos"].insert_one(video_record)
    SHARED_DATA[username] = "Returning Output"
    return {
        "status": "success",
        "video_url": video_url,
        "is_flagged": is_flagged
    }

@router.get("/getVideos")
async def get_user_videos(current_user: dict = Depends(get_current_user)):
    username = current_user.get("username")
    
    cursor = db["videos"].find({"username": username})
    videos = await cursor.to_list(length=100)
    
    # Standardize output: Convert ObjectId to string for JSON serialization
    for v in videos:
        v["_id"] = str(v["_id"])
    
    return {"videos": videos}

@router.delete("/deleteVideo/{video_id}")
async def delete_video(video_id: str, current_user: dict = Depends(get_current_user)):
    username = current_user.get("username")

    # 1. Fetch metadata
    video = await db["videos"].find_one({
        "_id": ObjectId(video_id), 
        "username": username
    })

    if not video:
        raise HTTPException(status_code=404, detail="Video not found or unauthorized")

    # 2. Delete from GCS
    video_url = video.get("video_url")
    gcs_deleted = delete_gcs_video(video_url)
    
    if not gcs_deleted:
        raise HTTPException(
            status_code=500, 
            detail="Failed to delete video file from cloud storage"
        )

    # 3. Delete from MongoDB
    await db["videos"].delete_one({"_id": ObjectId(video_id)})

    return {"status": "success", "message": "Video and metadata removed"}

@router.get("/signed-url/")
async def get_gcs_signed_url(video_id: str):
    # 2. Validate and Fetch from MongoDB
    if not ObjectId.is_valid(video_id):
        raise HTTPException(status_code=400, detail="Invalid Object ID")

    video_doc = await db.videos.find_one({"_id": ObjectId(video_id)})
    
    if not video_doc:
        raise HTTPException(status_code=404, detail="Video not found")

    # 3. Extract GCS details
    # Assuming video_url is stored as 'gs://bucket-name/path/to/video.mp4'
    gcs_url = video_doc.get("video_url") 
    if not gcs_url.startswith("gs://"):
        raise HTTPException(status_code=400, detail="Invalid GCS URL format")

    # Remove 'gs://' and split into bucket and blob name
    path_parts = gcs_url.replace("gs://", "").split("/", 1)
    bucket_name = path_parts[0]
    blob_name = path_parts[1]

    # 4. Generate Signed URL
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=60),  # Valid for 1 hour
            method="GET",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS Error: {str(e)}")

    return {"signed_url": signed_url}
