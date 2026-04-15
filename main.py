import uuid
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional, List
import requests

app = FastAPI()

# URL del servidor local
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


def enviar_a_local(audio_bytes, metadata, categoria, nombre_archivo="audio.wav"):
    files = {
        "audio": (nombre_archivo, audio_bytes, "audio/wav")
    }

    data = {
        "metadata": json.dumps(metadata),
        "categoria": categoria
    }

    response = requests.post(BASE_URL, files=files, data=data, timeout=60)
    return response.status_code, response.text


@app.post("/ingest")
async def ingest(
    audios: List[UploadFile] = File(...),
    metadata: Optional[str] = Form(None)
):
    try:
        # Validar que lleguen exactamente 4 archivos
        if len(audios) != 4:
            return {
                "status": "error",
                "message": f"Debes enviar exactamente 4 audios. Recibidos: {len(audios)}"
            }

        # Metadata base
        if metadata:
            data_base = json.loads(metadata)
        else:
            data_base = generar_json_base()

        categoria = determinar_categoria(data_base)
        resultados = []

        for idx, audio in enumerate(audios, start=1):
            file_id = str(uuid.uuid4())

            # Leer contenido del audio
            audio_bytes = await audio.read()

            # Copia independiente del metadata para cada archivo
            data_audio = json.loads(json.dumps(data_base))
            data_audio["file_id"] = file_id
            data_audio["indice_audio"] = idx
            data_audio["nombre_original"] = audio.filename

            # Nombre sugerido del archivo
            extension = ".wav"
            if audio.filename and "." in audio.filename:
                extension = "." + audio.filename.split(".")[-1].lower()

            nombre_archivo = f"{file_id}{extension}"

            # Enviar al servidor local
            status, resp = enviar_a_local(
                audio_bytes=audio_bytes,
                metadata=data_audio,
                categoria=categoria,
                nombre_archivo=nombre_archivo
            )

            resultados.append({
                "indice": idx,
                "file_id": file_id,
                "archivo_original": audio.filename,
                "archivo_enviado": nombre_archivo,
                "categoria": categoria,
                "upload_status": status,
                "respuesta_local": resp
            })

        return {
            "status": "ok",
            "cantidad_audios": len(audios),
            "categoria": categoria,
            "resultados": resultados
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}