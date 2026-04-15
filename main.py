import uuid
import json
from copy import deepcopy
from fastapi import FastAPI, UploadFile, File, Form
from typing import List
import requests

app = FastAPI()

BASE_URL = "http://172.16.10.200:5002/api/upload"

FOCOS = [
    {"foco_auscultacion": "Mitral", "codigo_foco": "01"},
    {"foco_auscultacion": "Tricuspídeo", "codigo_foco": "03"},
    {"foco_auscultacion": "Aórtico", "codigo_foco": "02"},
    {"foco_auscultacion": "Pulmonar", "codigo_foco": "04"},
]


def determinar_categoria(data: dict) -> str:
    cat = data.get("diagnostico", {}).get("categoria_anomalia")
    if cat is None:
        return "unknown"
    elif str(cat).lower() == "normal":
        return "normal"
    else:
        return "anormal"


def enviar_a_local(audio_bytes: bytes, metadata: dict, categoria: str, filename: str):
    files = {
        "audio": (filename, audio_bytes, "audio/wav")
    }

    data = {
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "categoria": categoria
    }

    response = requests.post(BASE_URL, files=files, data=data, timeout=60)
    return response.status_code, response.text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(
    audios: List[UploadFile] = File(...),
    metadata: str = Form(...)
):
    try:
        if len(audios) != 4:
            return {
                "status": "error",
                "message": f"Debes enviar exactamente 4 audios. Recibidos: {len(audios)}"
            }

        data_base = json.loads(metadata)

        resultados = []

        for i, audio in enumerate(audios):
            foco = FOCOS[i]

            # leer bytes del audio
            audio_bytes = await audio.read()

            # clonar metadata base para no alterar el original
            data_audio = deepcopy(data_base)

            # actualizar foco
            data_audio["diagnostico"]["foco_auscultacion"] = foco["foco_auscultacion"]
            data_audio["diagnostico"]["codigo_foco"] = foco["codigo_foco"]

            # categoría según categoria_anomalia
            categoria = determinar_categoria(data_audio)

            # nombre sugerido del archivo
            request_file_id = str(uuid.uuid4())
            filename = f"{request_file_id}.wav"

            status_code, response_text = enviar_a_local(
                audio_bytes=audio_bytes,
                metadata=data_audio,
                categoria=categoria,
                filename=filename
            )

            resultados.append({
                "indice": i + 1,
                "archivo_original": audio.filename,
                "foco_auscultacion": foco["foco_auscultacion"],
                "codigo_foco": foco["codigo_foco"],
                "categoria": categoria,
                "upload_status": status_code,
                "respuesta_local": response_text
            })

        return {
            "status": "ok",
            "procesados": 4,
            "resultados": resultados
        }

    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "El campo metadata no contiene un JSON válido"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }