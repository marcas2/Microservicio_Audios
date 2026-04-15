import uuid
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional
import requests

app = FastAPI()

# URL base del server local (Apache)
BASE_URL = "http://172.16.10.200:5002/api/upload"

def generar_json_base():
    return {
        "metadata": {
            "fecha_grabacion": datetime.now().isoformat(),
            "origen": "auto"
        },
        "diagnostico": {
            "categoria_anomalia": None
        }
    }

def determinar_categoria(data):
    cat = data.get("diagnostico", {}).get("categoria_anomalia")
    if cat is None:
        return "unknown"
    elif str(cat).lower() == "normal":
        return "normal"
    else:
        return "anormal"

def subir_archivo(url, contenido, content_type="application/octet-stream"):
    headers = {"Content-Type": content_type}
    response = requests.put(url, data=contenido, headers=headers)
    return response.status_code, response.text

@app.post("/ingest")
async def ingest(
    audio: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    try:
        file_id = str(uuid.uuid4())

        # JSON
        if metadata:
            data = json.loads(metadata)
        else:
            data = generar_json_base()

        categoria = determinar_categoria(data)

        # Nombres
        audio_name = f"{file_id}.wav"
        json_name = f"{file_id}.json"

        # URLs destino en Apache
        audio_url = f"{BASE_URL}/Audios/{categoria}/{audio_name}"
        json_url = f"{BASE_URL}/audios-json/{categoria}/{json_name}"

        # Leer audio
        audio_bytes = await audio.read()

        # Subir audio
        status_audio, resp_audio = subir_archivo(audio_url, audio_bytes)

        # Preparar JSON
        data["file_id"] = file_id
        json_bytes = json.dumps(data, indent=4).encode("utf-8")

        # Subir JSON
        status_json, resp_json = subir_archivo(json_url, json_bytes, "application/json")

        return {
            "status": "ok",
            "file_id": file_id,
            "categoria": categoria,
            "audio_status": status_audio,
            "json_status": status_json
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}