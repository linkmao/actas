import json
import os
import re
from pathlib import Path

from . import db

KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge" / "manual_convivencia.json"

TOKEN_LABELS = {
    "estudiante": "Estudiante",
    "acudiente": "Acudiente",
    "docente": "Docente",
    "directivo": "Directivo",
    "orientador": "Orientador",
    "otro": "Persona",
}

# Proveedores de IA soportados. `default_model` es solo una sugerencia editable desde
# Configuración: los nombres de modelo cambian con el tiempo y el usuario puede ajustarlo.
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "default_model": "claude-sonnet-5",
        "env_key": "ANTHROPIC_API_KEY",
        "help_url": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "default_model": "gpt-5.1",
        "env_key": "OPENAI_API_KEY",
        "help_url": "https://platform.openai.com/api-keys",
    },
    "google": {
        "label": "Google (Gemini)",
        "default_model": "gemini-2.5-flash",
        "env_key": "GOOGLE_API_KEY",
        "help_url": "https://aistudio.google.com/apikey",
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-v4-flash",
        "env_key": "DEEPSEEK_API_KEY",
        "help_url": "https://platform.deepseek.com/api_keys",
        "base_url": "https://api.deepseek.com",
    },
}


class AIError(Exception):
    pass


def _load_knowledge() -> dict:
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_anonymization(personas: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Returns (personas_anonimizadas, token_a_nombre_real)."""
    counters: dict[str, int] = {}
    token_map: dict[str, str] = {}
    personas_anon = []
    for persona in personas:
        tipo = (persona.get("tipo") or "otro").lower()
        label = TOKEN_LABELS.get(tipo, "Persona")
        counters[label] = counters.get(label, 0) + 1
        token = f"{label} {counters[label]}"
        nombre_real = persona.get("nombre", "").strip()
        if nombre_real:
            token_map[token] = nombre_real
        personas_anon.append({
            "token": token,
            "rol_cargo": persona.get("rol_cargo", ""),
            "tipo": tipo,
        })
    return personas_anon, token_map


def _anonymize_text(text: str, personas: list[dict], token_map: dict[str, str]) -> str:
    """Reemplaza nombres reales (y primeros nombres) por sus tokens en la descripción libre."""
    result = text
    replacements = []
    for token, nombre_real in token_map.items():
        replacements.append((nombre_real, token))
        partes = nombre_real.split()
        if len(partes) > 1:
            replacements.append((partes[0], token))
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    for nombre, token in replacements:
        if not nombre:
            continue
        pattern = re.compile(re.escape(nombre), re.IGNORECASE)
        result = pattern.sub(token, result)
    return result


def _deanonymize(value, token_map: dict[str, str]):
    if isinstance(value, str):
        for token, nombre_real in token_map.items():
            value = re.sub(re.escape(token), nombre_real, value, flags=re.IGNORECASE)
        return value
    if isinstance(value, list):
        return [_deanonymize(v, token_map) for v in value]
    if isinstance(value, dict):
        return {k: _deanonymize(v, token_map) for k, v in value.items()}
    return value


SYSTEM_PROMPT = """Eres un asistente experto en el Acuerdo de Convivencia (Manual) de una institución \
educativa colombiana, regido por la Ley 1620 de 2013 y el Decreto 1965 de 2013. Tu tarea es apoyar a un \
coordinador de convivencia a redactar el cuerpo de un acta institucional.

Recibirás: (1) la descripción breve de una situación de convivencia, con los nombres de las personas ya \
reemplazados por tokens de rol (Estudiante 1, Acudiente 1, Docente 1, etc. - debes usar EXACTAMENTE esos \
mismos tokens en tu respuesta, nunca inventes nombres propios), y (2) un extracto del Acuerdo de Convivencia \
con la tipificación de situaciones (Tipo I, II, III) y el catálogo de acciones pedagógicas (consensuales, \
restaurativas, retributivas).

Debes responder ÚNICAMENTE con un objeto JSON válido (sin texto adicional, sin markdown) con esta forma exacta:
{
  "tipificacion": {"tipo": "I|II|III", "articulo": "14.x", "conducta": "conducta específica del catálogo que aplica", "justificacion": "por qué aplica, en 2-3 frases"},
  "narrativa_antecedentes": "texto en tono institucional y formal, en tercera persona, que amplía los hechos descritos citando el/los artículo(s) pertinente(s) del Acuerdo de Convivencia. 1 a 3 párrafos.",
  "acciones_propuestas": [
    {"descripcion": "acción concreta y accionable", "categoria": "consensual|restaurativa|retributiva", "articulo": "17.x letra", "responsable_sugerido": "quién la ejecuta o hace seguimiento"}
  ],
  "acuerdos_texto": "resumen narrativo de los acuerdos/compromisos adoptados, en tono institucional, coherente con las acciones propuestas"
}

Reglas importantes:
- Nunca sugieras acciones retributivas (17.3) para situaciones Tipo I salvo reincidencia explícita agotando \
  mecanismos previos; prioriza siempre acciones consensuales y restaurativas (Art. 9: prohibidas las sanciones \
  crueles, humillantes o degradantes).
- Cita artículos reales tomados del extracto entregado, nunca inventes numeración.
- Propón entre 2 y 4 acciones, coherentes con el tipo de situación y proporcionales a los hechos.
- Usa siempre los tokens de rol tal cual te los dieron (Estudiante 1, Acudiente 1, ...), nunca nombres propios.
- Escribe los tokens exactamente así, sin anteponerles artículos (di "Estudiante 1 publicó..." y no "el/la \
  Estudiante 1 publicó..."), ya que el token será reemplazado por un nombre propio y el artículo antepuesto \
  quedaría gramaticalmente incorrecto.
"""


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def get_config_overview() -> dict:
    """Resumen seguro de la configuración (nunca expone la API key completa)."""
    conn = db.get_connection()
    try:
        cfg = db.get_config_values(conn)
    finally:
        conn.close()
    provider = cfg.get("provider") or "anthropic"
    if provider not in PROVIDERS:
        provider = "anthropic"

    providers_info = {}
    for key, meta in PROVIDERS.items():
        saved_key = cfg.get(f"{key}_api_key") or ""
        env_key = os.environ.get(meta["env_key"], "")
        effective_key = saved_key or env_key
        providers_info[key] = {
            "label": meta["label"],
            "help_url": meta["help_url"],
            "default_model": meta["default_model"],
            "model": cfg.get(f"{key}_model") or meta["default_model"],
            "configured": bool(effective_key),
            "key_preview": _mask_key(effective_key),
            "from_env": bool(env_key) and not saved_key,
        }
    return {"provider": provider, "providers": providers_info}


def set_config(provider: str, api_key: str | None, model: str | None):
    if provider not in PROVIDERS:
        raise AIError(f"Proveedor no soportado: {provider}")
    updates = {"provider": provider}
    if api_key:
        updates[f"{provider}_api_key"] = api_key.strip()
    if model:
        updates[f"{provider}_model"] = model.strip()
    conn = db.get_connection()
    try:
        db.set_config_values(conn, updates)
    finally:
        conn.close()
    return get_config_overview()


def clear_config(provider: str):
    if provider not in PROVIDERS:
        raise AIError(f"Proveedor no soportado: {provider}")
    conn = db.get_connection()
    try:
        db.set_config_values(conn, {f"{provider}_api_key": "", f"{provider}_model": ""})
    finally:
        conn.close()
    return get_config_overview()


def _get_active_settings() -> dict:
    conn = db.get_connection()
    try:
        cfg = db.get_config_values(conn)
    finally:
        conn.close()
    provider = cfg.get("provider") or "anthropic"
    if provider not in PROVIDERS:
        provider = "anthropic"
    meta = PROVIDERS[provider]
    api_key = cfg.get(f"{provider}_api_key") or os.environ.get(meta["env_key"], "")
    model = cfg.get(f"{provider}_model") or meta["default_model"]
    return {"provider": provider, "api_key": api_key, "model": model}


def _call_anthropic(api_key: str, model: str, user_content: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_openai_compatible(api_key: str, model: str, user_content: str, base_url: str | None = None) -> str:
    """Sirve tanto a OpenAI como a APIs compatibles con su formato de chat (p. ej. DeepSeek)."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIError("Falta instalar el paquete 'openai' (ejecuta: pip install openai).") from exc

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content or ""


def _call_openai(api_key: str, model: str, user_content: str) -> str:
    return _call_openai_compatible(api_key, model, user_content)


def _call_deepseek(api_key: str, model: str, user_content: str) -> str:
    return _call_openai_compatible(api_key, model, user_content, base_url=PROVIDERS["deepseek"]["base_url"])


def _call_google(api_key: str, model: str, user_content: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise AIError("Falta instalar el paquete 'google-genai' (ejecuta: pip install google-genai).") from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text or ""


_CALLERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
    "deepseek": _call_deepseek,
}


def analizar_situacion(personas: list[dict], descripcion_breve: str) -> dict:
    settings = _get_active_settings()
    provider, api_key, model = settings["provider"], settings["api_key"], settings["model"]

    if not api_key:
        raise AIError(
            f"No hay una API key configurada para {PROVIDERS[provider]['label']}. "
            "Ve a la pestaña 'Configuración' e ingresa tu API key."
        )

    personas_anon, token_map = _build_anonymization(personas)
    descripcion_anon = _anonymize_text(descripcion_breve, personas, token_map)
    knowledge = _load_knowledge()

    user_content = json.dumps({
        "personas_involucradas": personas_anon,
        "descripcion_breve_anonimizada": descripcion_anon,
        "acuerdo_de_convivencia": knowledge,
    }, ensure_ascii=False, indent=2)

    try:
        raw_text = _CALLERS[provider](api_key, model, user_content)
    except AIError:
        raise
    except Exception as exc:  # noqa: BLE001 - se traduce a error de dominio para la API
        raise AIError(f"Error llamando a la API de {PROVIDERS[provider]['label']}: {exc}") from exc

    raw_text = (raw_text or "").strip()
    raw_text_limpio = re.sub(r"^```(json)?|```$", "", raw_text, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw_text_limpio)
    except json.JSONDecodeError as exc:
        raise AIError(f"La IA no devolvió un JSON válido: {exc}\n\nRespuesta recibida:\n{raw_text}") from exc

    resultado = _deanonymize(parsed, token_map)
    # Información de depuración para la sección "Avanzado": se guarda tal como se envió/recibió
    # (con los tokens anonimizados, nunca con nombres reales), no se pasa por _deanonymize.
    resultado["_debug"] = {
        "proveedor": PROVIDERS[provider]["label"],
        "modelo": model,
        "prompt_sistema": SYSTEM_PROMPT,
        "prompt_usuario": user_content,
        "respuesta_cruda": raw_text,
    }
    return resultado
