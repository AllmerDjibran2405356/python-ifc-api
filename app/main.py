# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile
import os
from app.ifc_processor import parse_all_objects

app = FastAPI()

@app.post("/convert-ifc")
async def convert_ifc(file: UploadFile = File(...)):
    try:
        # Buat file tmp TANPA lock (Windows compatible)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(await file.read())
            tmp.flush()
            temp_path = tmp.name

        # Proses IFC
        result_array = parse_all_objects(temp_path)

        # Hapus file temp setelah selesai
        os.remove(temp_path)

        return JSONResponse({
            "status": "success",
            "data": result_array
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)
