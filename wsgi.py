# wsgi.py
# File ini untuk kompatibilitas dengan gunicorn
from app.main import app

if __name__ == "__main__":
    # Untuk running lokal jika diperlukan
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)