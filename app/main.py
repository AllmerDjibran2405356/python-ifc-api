from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
import os
from .ifc_processor import process_ifc

app = FastAPI(
    title="IFC to JSON Converter",
    version="1.0.0",
    description="Convert IFC files to structured JSON using IfcOpenShell"
)

# Allow Laravel to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "Python IFC API is running"}

@app.post("/convert-ifc")
async def convert_ifc(file: UploadFile = File(...)):
    try:
        # Save IFC file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Process IFC
        result = process_ifc(tmp_path)

        # Remove temp file
        os.remove(tmp_path)

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
