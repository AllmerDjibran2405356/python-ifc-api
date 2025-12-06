from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import json

from parser import parse_all_objects  # parser kamu (adapted)

app = FastAPI(title="IFC Parser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok"}

@app.post("/parse-ifc")
async def parse_ifc(file: UploadFile = File(...)):
    """
    Terima file IFC (upload), simpan sementara, parse dengan parser.py,
    lalu kembalikan JSON array hasil parsing.
    """
    # simpan file sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # parse_all_objects harus mengembalikan list/dict sesuai contoh JSON kamu
        result = parse_all_objects(tmp_path)

        # Pastikan result dapat diserialisasi
        return result

    except Exception as e:
        return {"error": str(e)}

    finally:
        try:
            os.remove(tmp_path)
        except:
            pass
