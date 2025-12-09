# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import shutil
from app.ifc_processor import parse_all_objects

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "temp_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/convert-ifc")
async def convert_ifc(file: UploadFile = File(...)):
    try:
        # Simpan temp
        temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Convert IFC → ARRAY JSON
        result_array = parse_all_objects(temp_path)

        # Hapus file temp
        os.remove(temp_path)

        # Kembalikan JSON ke Laravel
        return JSONResponse({
            "status": "success",
            "data": result_array
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)
