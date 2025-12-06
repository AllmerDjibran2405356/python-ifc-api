from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from parser import parse_all_objects
import tempfile
import os

app = FastAPI(
    title="IFC Parser API",
    version="1.0.0",
)

# CORS untuk semua domain agar Laravel bisa request
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/parse-ifc")
async def parse_ifc(file: UploadFile = File(...)):
    """
    API menerima file IFC → menyimpannya sementara → memanggil parser → retur JSON
    """

    # Simpan file sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Proses IFC
        result = parse_all_objects(tmp_path)
        return result

    except Exception as e:
        return {"error": str(e)}

    finally:
        # Hapus file sementara
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
