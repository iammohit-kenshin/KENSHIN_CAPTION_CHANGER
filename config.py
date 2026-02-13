import os

class Config:
    API_ID = int(os.environ.get("37407868")) # Apni API ID yahan daalein ya Env var use kare
    API_HASH = os.environ.get("d7d3bff9f7cf9f3b111129bdbd13a065")
    BOT_TOKEN = os.environ.get("8341261215:AAFKnBp228F6gc8JCXuLw80o-ZUyu7xUmRI")
    OWNER_ID = int(os.environ.get("OWNER_ID", "6728678197")) # Tumhara ID
