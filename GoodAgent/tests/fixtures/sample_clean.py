import os
import uuid

COLOR_PRIMARY = "#3B82F6"
SECRET_KEY = os.environ.get("SECRET_KEY")
SESSION_ID = str(uuid.uuid4())
COMMIT_HASH = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A\n-----END PUBLIC KEY-----"
