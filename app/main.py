import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from . import ai, db
from .ai import analizar_situacion, AIError
from .docgen import generar_acta_docx

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Actas de Convivencia")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Persona(BaseModel):
    nombre: str
    rol_cargo: str = ""
    tipo: str = "otro"  # estudiante | acudiente | docente | directivo | orientador | otro


class AnalizarRequest(BaseModel):
    personas: list[Persona]
    descripcion_breve: str


class AccionPropuesta(BaseModel):
    descripcion: str
    categoria: str = ""
    articulo: str = ""
    responsable_sugerido: str = ""


class ProximaReunion(BaseModel):
    fecha: str = ""
    hora: str = ""
    lugar: str = ""


class ConfigUpdate(BaseModel):
    provider: str
    api_key: str | None = None
    model: str | None = None


class ActaPayload(BaseModel):
    numero_acta: int | None = None
    fecha: str
    hora_inicio: str = ""
    hora_fin: str = ""
    lugar: str = "Coordinación"
    elaborada_por: str = ""
    personas: list[Persona]
    descripcion_breve: str
    tipificacion: dict | None = None
    narrativa_antecedentes: str = ""
    acciones: list[AccionPropuesta] = []
    acuerdos_texto: str = ""
    proxima_reunion: ProximaReunion | None = None
    estado: str = "borrador"


@app.post("/api/analizar")
def analizar(payload: AnalizarRequest):
    try:
        resultado = analizar_situacion(
            [p.model_dump() for p in payload.personas],
            payload.descripcion_breve,
        )
    except AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return resultado


@app.get("/api/config")
def obtener_config():
    return ai.get_config_overview()


@app.post("/api/config")
def guardar_config(payload: ConfigUpdate):
    try:
        return ai.set_config(payload.provider, payload.api_key, payload.model)
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/config/{provider}")
def borrar_config(provider: str):
    try:
        return ai.clear_config(provider)
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/actas")
def listar_actas(q: str | None = None):
    conn = db.get_connection()
    try:
        return db.list_actas(conn, search=q)
    finally:
        conn.close()


@app.get("/api/actas/{acta_id}")
def obtener_acta(acta_id: int):
    conn = db.get_connection()
    try:
        acta = db.get_acta(conn, acta_id)
    finally:
        conn.close()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    return acta


@app.post("/api/actas")
def crear_acta(payload: ActaPayload):
    conn = db.get_connection()
    try:
        data = payload.model_dump()
        acta_id = db.create_acta(conn, data)
        return db.get_acta(conn, acta_id)
    finally:
        conn.close()


@app.put("/api/actas/{acta_id}")
def actualizar_acta(acta_id: int, payload: ActaPayload):
    conn = db.get_connection()
    try:
        if not db.get_acta(conn, acta_id):
            raise HTTPException(status_code=404, detail="Acta no encontrada")
        db.update_acta(conn, acta_id, payload.model_dump())
        return db.get_acta(conn, acta_id)
    finally:
        conn.close()


@app.post("/api/actas/{acta_id}/generar-docx")
def generar_docx(acta_id: int):
    conn = db.get_connection()
    try:
        acta = db.get_acta(conn, acta_id)
        if not acta:
            raise HTTPException(status_code=404, detail="Acta no encontrada")
        fecha_archivo = (acta.get("fecha") or "").replace(" ", "_").replace("/", "-")
        nombre_archivo = f"Acta_{acta['numero_acta']}_{fecha_archivo}.docx"
        output_path = OUTPUT_DIR / nombre_archivo
        generar_acta_docx(acta, output_path)
        db.update_acta(conn, acta_id, {"archivo_path": str(output_path), "estado": "final"})
        return {"archivo": nombre_archivo, "url": f"/api/actas/{acta_id}/descargar"}
    finally:
        conn.close()


@app.get("/api/actas/{acta_id}/descargar")
def descargar_docx(acta_id: int):
    conn = db.get_connection()
    try:
        acta = db.get_acta(conn, acta_id)
    finally:
        conn.close()
    if not acta or not acta.get("archivo_path"):
        raise HTTPException(status_code=404, detail="Esta acta aún no tiene un documento generado")
    path = Path(acta["archivo_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="El archivo generado ya no existe en disco")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.name,
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
