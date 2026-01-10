import asyncio
import jwt
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends, HTTPException
from google.cloud import storage, videointelligence
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from routes.auth import get_current_user
from bson import ObjectId
load_dotenv()

router = APIRouter()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
BUCKET_NAME = os.getenv("BUCKET_NAME")
MONGO_URI = os.getenv("MONGO_URI")


# Clients
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["pulse_db"]
storage_client = storage.Client()
video_client = videointelligence.VideoIntelligenceServiceClient()

async def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("username") 
    except jwt.PyJWTError:
        return None
    
from google.cloud import storage
from urllib.parse import urlparse

def delete_gcs_video(gcs_uri: str):
    """
    Deletes a file from GCS based on its path (gs://bucket_name/blob_name)
    """
    try:
        # 1. Parse the URI (gs://bucket-name/path/to/video.mp4)
        parsed_url = urlparse(gcs_uri)
        bucket_name = parsed_url.netloc
        # .lstrip("/") removes the leading slash from the path
        blob_name = parsed_url.path.lstrip("/")

        # 2. Initialize client and bucket
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # 3. Delete the blob
        blob.delete()
        return True
    except Exception as e:
        print(f"Error deleting GCS object: {e}")
        return False
    

@router.websocket("/ws/upload")
async def video_upload_websocket(websocket: WebSocket, token: str = None):
    # 1. Authenticate via Token
    await websocket.accept()
    username = await get_user_from_token(token)
    
    if not username:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # 2. Receive Video Bytes
        await websocket.send_text("Status: Authenticated. Sending video...")
        video_data = await websocket.receive_bytes()
        
        filename = f"{username}_{uuid.uuid4()}.mp4"
        gcs_uri = f"gs://{BUCKET_NAME}/{filename}"

        # 3. Upload to GCS
        await websocket.send_text("Status: Uploading to Cloud Storage...")
        blob = storage_client.bucket(BUCKET_NAME).blob(filename)
        blob.upload_from_string(video_data, content_type="video/mp4")

        # 4. Request Video Intelligence Analysis
        await websocket.send_text("Status: Analyzing for explicit content...")
        operation = video_client.annotate_video(
            request={
                "features": [videointelligence.Feature.EXPLICIT_CONTENT_DETECTION],
                "input_uri": gcs_uri
            }
        )

        # 5. Poll for Results
        while not operation.done():
            await websocket.send_text("Status: Processing AI labels...")
            await asyncio.sleep(3)

        result = operation.result()
        
        # 6. Process Flags
        frames = result.annotation_results[0].explicit_content_annotations.frames
        is_flagged = any(f.pornography_likelihood >= 4 for f in frames) # 4 = LIKELY
        description = "Inappropriate content detected" if is_flagged else "Content clean"

        # 7. Save to MongoDB
        await db.videos.insert_one({
            "username": username,
            "video_path": gcs_uri,
            "flag": is_flagged,
            "description": description
        })
        
        await websocket.send_json({"status": "Success", "flagged": is_flagged})

    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        await websocket.close()

@router.get("/getVideos")
def getVideo(user: dict = Depends(get_current_user)):
    username = user.get("username")
    
    # 2. Query the 'videos' collection for metadata
    # Assuming 'db' is your motor client database instance
    cursor = db["videos"].find({"username": username})
    
    # 3. Convert cursor to list
    videos = cursor.to_list(length=100)
    
    if not videos:
        return {"message": "No videos found", "videos": []}

    # 4. Return metadata (FastAPI handles JSON serialization)
    return {"videos": videos}
    

# @router.delete("/deleteVideo/{video_id}")
# async def delete_video(video_id: str, user: dict = Depends(get_current_user)):
#     username = user.get("username")
    
#     # 1. Fetch metadata first to get the GCS URI
#     video = await db["videos"].find_one({
#         "_id": ObjectId(video_id), 
#         "username": username
#     })

#     if not video:
#         raise HTTPException(status_code=404, detail="Video not found")

#     # 2. Extract blob name from GCS URI (e.g., "gs://bucket/folder/video.mp4")
#     # Assuming video_path is the full URI
#     gcs_uri = video.get("video_path")
#     blob_name = gcs_uri.replace(f"gs://{BUCKET_NAME}/", "")

#     try:
#         # 3. Delete from Google Cloud Storage
#         bucket = storage_client.bucket(BUCKET_NAME)
#         blob = bucket.blob(blob_name)
#         blob.delete()
        
#         # 4. Delete from MongoDB
#         await db["videos"].delete_one({"_id": ObjectId(video_id)})
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")

#     return {"message": "Video and metadata deleted successfully"}

@router.delete("/deleteVideo/{video_id}")
async def delete_video(video_id: str, user: dict = Depends(get_current_user)):
    # 1. Get metadata from MongoDB
    video = await db["videos"].find_one({
        "_id": ObjectId(video_id),
        "username": user.get("username")
    })

    if not video:
        raise HTTPException(status_code=404, detail="Video metadata not found")

    # 2. Delete from GCP Storage using the path from DB
    gcs_deleted = delete_gcs_video(video["video_path"])
    
    if not gcs_deleted:
        raise HTTPException(status_code=500, detail="Failed to delete video file from cloud storage")

    # 3. Delete from MongoDB only if GCP deletion was successful
    await db["videos"].delete_one({"_id": ObjectId(video_id)})

    return {"status": "success", "message": "Video and metadata removed"}
