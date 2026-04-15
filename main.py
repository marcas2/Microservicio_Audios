import json
from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
import requests

app = FastAPI()

BASE_URL = "http://172.16.10.200:5002/api/upload"


def determinar_categoria(data: dict) -> str:
    diagnostico = data.get("diagnostico", {})
    categoria_anomalia = diagnostico.get("categoria_anomalia")
    estado = diagnostico.get("estado")

    if categoria_anomalia is not None:
        if str(categoria_anomalia).strip().lower() == "normal":
            return "normal"
        return "anormal"

    if estado is not None:
        if str(estado).strip().lower() == "normal":
            return "normal"
        return "anormal"

    return "unknown"


def enviar_a_local(
    audio_principal_bytes: bytes,
    audio_ecg_bytes: bytes,
    audio_ecg_1_bytes: bytes,
    audio_ecg_2_bytes: bytes,
    metadata: dict,
    categoria: str,
    original_names: dict
):
    files = {
        "audio_principal": (
            original_names["audio_principal"],
            audio_principal_bytes,
            "audio/wav"
        ),
        "audio_ecg": (
            original_names["audio_ecg"],
            audio_ecg_bytes,
            "audio/wav"
        ),
        "audio_ecg_1": (
            original_names["audio_ecg_1"],
            audio_ecg_1_bytes,
            "audio/wav"
        ),
        "audio_ecg_2": (
            original_names["audio_ecg_2"],
            audio_ecg_2_bytes,
            "audio/wav"
        )
    }

    data = {
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "categoria": categoria
    }

    response = requests.post(BASE_URL, files=files, data=data, timeout=120)
    return response.status_code, response.text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(
    audios: List[UploadFile] = File(...),
    metadata: Optional[str] = Form(None),
    metadata_file: Optional[UploadFile] = File(None)
):
    try:
        if len(audios) != 4:
            return {
                "status": "error",
                "message": f"Debes enviar exactamente 4 audios. Recibidos: {len(audios)}"
            }

        if metadata_file is not None:
            raw = await metadata_file.read()
            data_base = json.loads(raw.decode("utf-8"))
        elif metadata is not None:
            data_base = json.loads(metadata)
        else:
            return {
                "status": "error",
                "message": "Debes enviar metadata o metadata_file"
            }

        categoria = determinar_categoria(data_base)

        audio_principal_bytes = await audios[0].read()
        audio_ecg_bytes = await audios[1].read()
        audio_ecg_1_bytes = await audios[2].read()
        audio_ecg_2_bytes = await audios[3].read()

        original_names = {
            "audio_principal": audios[0].filename or "audio_principal.wav",
            "audio_ecg": audios[1].filename or "audio_ecg.wav",
            "audio_ecg_1": audios[2].filename or "audio_ecg_1.wav",
            "audio_ecg_2": audios[3].filename or "audio_ecg_2.wav"
        }

        status_code, response_text = enviar_a_local(
            audio_principal_bytes=audio_principal_bytes,
            audio_ecg_bytes=audio_ecg_bytes,
            audio_ecg_1_bytes=audio_ecg_1_bytes,
            audio_ecg_2_bytes=audio_ecg_2_bytes,
            metadata=data_base,
            categoria=categoria,
            original_names=original_names
        )

        return {
            "status": "ok",
            "categoria": categoria,
            "upload_status": status_code,
            "respuesta_local": response_text
        }

    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "El metadata no contiene un JSON válido"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }