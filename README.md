# Pulse Backend

A high-performance FastAPI backend designed for secure video management. This service handles user authentication, automated video content moderation using AI, and secure cloud storage.

## 🚀 Live Links
* **Frontend (Vercel):** [https://pulse-frontend-khaki.vercel.app/](https://pulse-frontend-khaki.vercel.app/)
* **Backend (Render):** [https://pulsechallenge.onrender.com/](https://pulsechallenge.onrender.com/)

> **Note:** The backend is hosted on a service with "cold starts." If the app hasn't been used recently, the first request may take a few moments to initialize.

---

## 🏗 Architecture Overview

Pulse utilizes a modern, hybrid cloud architecture to ensure scalability and data integrity:



1.  **Identity Management (Supabase + Argon2):** * User profiles and credentials are stored in **Supabase (PostgreSQL)**.
    * Passwords are secured using **Argon2** hashing.
    * Session management is handled via **JWT (JSON Web Tokens)**.

2.  **Object Storage (Google Cloud Storage):**
    * Videos are uploaded to **GCS** with unique UUIDs.
    * To keep files private, the system generates **Signed URLs** that expire after 60 minutes for secure viewing.

3.  **Content Moderation (GCP Video Intelligence):**
    * Every uploaded video is automatically processed by the **Google Video Intelligence API** to detect explicit or sensitive content.
    * Flagged statuses are saved immediately to the metadata.

4.  **Metadata Layer (MongoDB):**
    * Video metadata, descriptions, and moderation flags are stored in **MongoDB** for flexible, schema-less querying.

---

## 📂 Project Structure
```text
.
├── main.py              # App entry point & CORS middleware
├── database.py          # Connection clients for Supabase & MongoDB
├── routes/
│   ├── auth.py          # User registration, login & JWT utilities
│   └── video.py         # GCS uploads, AI moderation & video CRUD
├── requirements.txt     # Python dependencies
└── .env                 # Environment secrets
```
## ⚙️ Local Development & Initialization

Follow these steps to set up the environment:

### 1. Prerequisites
* A **Google Cloud** service account JSON key.
* A **Supabase** project and **MongoDB** instance.

### 2. Setup Steps
```bash
# 1. Create a virtual environment using uv
uv venv

# 2. Activate the environment
# Windows:
source .venv/scripts/activate
# Linux/Mac:
source .venv/bin/activate

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Set GCP Credentials path (replace with your actual file path)
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"

# 5. Run the server
uvicorn main:app --reload
```
## 🌐 Deployment

The project is currently deployed across the following platforms:

* **Frontend:** [Pulse on Vercel](https://pulse-frontend-khaki.vercel.app/)
* **Backend:** [Pulse API on Render](https://pulsechallenge.onrender.com/)

> [!NOTE]
> **Cold Start:** The backend is hosted on Render's free tier. If the service has been inactive, the first request may take **30-50 seconds** to spin up. Thank you for your patience!

---

## 🔒 Environment Variables

Ensure your `.env` file contains the following keys to ensure the application connects to all services correctly:

```env
FRONTEND_URL=
SECRET_KEY=
SUPABASE_URL=
SUPABASE_KEY=
MONGODB_URL=
BUCKET_NAME=
```
