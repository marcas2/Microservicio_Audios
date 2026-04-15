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

def enviar_a_local(audio_bytes, metadata, categoria):
    url = BASE_URL  # ya es /api/upload

    files = {
        "audio": ("audio.wav", audio_bytes, "audio/wav")
    }

    data = {
        "metadata": json.dumps(metadata),
        "categoria": categoria
    }

    response = requests.post(url, files=files, data=data)
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
        status, resp = enviar_a_local(audio_bytes, data, categoria)
        # Preparar JSON
        data["file_id"] = file_id
        json_bytes = json.dumps(data, indent=4).encode("utf-8")


        return {
            "status": "ok",
            "file_id": file_id,
            "categoria": categoria,
            "upload_status": status,
            "respuesta_local": resp
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}