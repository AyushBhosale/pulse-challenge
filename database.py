import os
from dotenv import load_dotenv
from supabase import create_client, Client
from pymongo import MongoClient
load_dotenv()

#supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

#mongo 
client = MongoClient(os.environ.get("MONGODB_URL"))
db = client['pulse_db']
def get_mongo_db():
    return db