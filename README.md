# Actas de Convivencia — IE Luis Carlos Galán Sarmiento

App local (escritorio) para diligenciar actas de convivencia: describes brevemente la situación,
la IA la amplía en tono institucional, la tipifica según el Acuerdo de Convivencia (Tipo I/II/III)
y propone acciones restaurativas del Art. 17; luego generas el acta en Word con el mismo formato
del acta de ejemplo.

## 1. Elegir proveedor de IA y obtener una API key (una sola vez)

La app soporta cuatro proveedores de IA — **Anthropic (Claude)**, **OpenAI (GPT)**, **Google (Gemini)**
y **DeepSeek** — y la API key se configura **desde la propia interfaz web**, en la pestaña
**Configuración**, sin tocar archivos. Solo necesitas la clave de UNO de estos proveedores (el que
prefieras):

- **Anthropic**: crea cuenta/inicia sesión en https://console.anthropic.com → **API Keys** → *Create Key*.
  La clave empieza por `sk-ant-...`.
- **OpenAI**: crea cuenta/inicia sesión en https://platform.openai.com/api-keys → *Create new secret key*.
  La clave empieza por `sk-...`.
- **Google (Gemini)**: entra a https://aistudio.google.com/apikey y genera una clave con tu cuenta de Google.
- **DeepSeek**: crea cuenta/inicia sesión en https://platform.deepseek.com/api_keys → *Create new API key*.
  La clave empieza por `sk-...`. DeepSeek requiere **saldo prepago** en tu cuenta (a diferencia de otros
  proveedores no basta con tener la clave activa); si al analizar ves el error "Insufficient Balance",
  agrega saldo en https://platform.deepseek.com/usage.

Ninguna clave se muestra completa de nuevo después de generarla, así que cópiala de inmediato.
Todas tienen un costo mínimo por uso (revisa la página de precios de cada proveedor); no hay suscripción,
se paga solo lo que se usa.

Una vez tengas la clave, entra a la pestaña **Configuración** de la app, pégala en el proveedor que
elegiste, marca ese proveedor como activo y da clic en **Guardar**. La clave queda guardada únicamente
en la base de datos local de este computador (`data/actas.db`) y nunca se vuelve a mostrar completa en
pantalla.

> **Alternativa avanzada**: si prefieres no escribir la clave en la interfaz, puedes copiar
> `.env.example` a `.env` y definir `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` o
> `DEEPSEEK_API_KEY` como variables de entorno. La app las usa automáticamente si no hay una clave
> guardada desde Configuración para ese proveedor.

## 2. Instalar y ejecutar

Requiere Python 3.11+ instalado.

```bash
pip install -r requirements.txt
python -m app.main
```

Abre el navegador en **http://localhost:8000**.

> **Si `pip install -r requirements.txt` falla en Windows** con un error tipo
> `Failed to write executable ... .exe.deleteme`, instala en tu carpeta de usuario:
> ```bash
> pip install --user -r requirements.txt
> ```

## 3. Uso

1. **Nueva acta**: el número de acta se autocompleta de forma consecutiva (editable si necesitas
   uno distinto), al igual que "Elaborada por" y la primera persona (quedan con los datos del
   coordinador por defecto). Completa fecha/hora/lugar, agrega las demás personas que intervienen
   (estudiante, acudiente, docente, directivo...) y escribe una descripción breve de la situación.
2. **Analizar con IA**: la app ampliará la descripción, propondrá la tipificación (Tipo I/II/III
   con el artículo correspondiente) y una lista de acciones restaurativas/pedagógicas.
   - Los nombres reales de las personas **nunca se envían** al servicio de IA: se reemplazan por
     roles genéricos ("Estudiante 1", "Acudiente 1"...) antes de la llamada y se reinsertan
     localmente en tu computador al recibir la respuesta.
3. **Revisa y edita** todo lo propuesto por la IA — el acta hace parte del debido proceso
   disciplinario, así que la redacción final es siempre responsabilidad del coordinador.
4. **Generar documento Word**: crea el archivo `.docx` con el mismo formato del acta de ejemplo y
   lo descarga automáticamente; el nombre del archivo sigue el patrón
   `NúmeroActa-dd.mm.aaaa NombreEstudiante Grado.docx` (ej. `3-20.02.2026 Jorge Cordoba 901.docx`;
   si no hay un estudiante registrado, usa `Sin Estudiante`). Después de generarlo, el formulario
   queda listo para la siguiente acta con el número consecutivo ya actualizado.
5. **Historial**: consulta, reabre o vuelve a descargar actas ya creadas (se guardan localmente
   en `data/actas.db`, un archivo SQLite en este mismo computador).
6. **Configuración**: cambia de proveedor de IA (Anthropic/OpenAI/Google), actualiza la API key o el
   modelo, o quita una clave guardada, en cualquier momento.

## Estructura del proyecto

```
app/
  main.py             API (FastAPI) y servidor de archivos estáticos
  db.py               Persistencia local (SQLite): actas y configuración del proveedor de IA
  ai.py               Anonimización + prompt + llamada al proveedor de IA (Anthropic/OpenAI/Google)
  docgen.py           Relleno del .docx a partir de la plantilla
  knowledge/manual_convivencia.json   Extracto curado del Acuerdo de Convivencia
  templates_docx/acta_template.docx   Plantilla (copia de ACTA DE EJEMPLO.docx)
static/               Frontend (HTML/CSS/JS sin build step)
data/actas.db         Base de datos local (se crea al primer uso)
output/               Documentos .docx generados
```

## Privacidad

Los datos de las actas (nombres, descripciones, decisiones) y la API key configurada quedan
**solo en este computador** (SQLite local + archivos .docx locales). Únicamente el texto anonimizado
de la descripción breve y los roles de las personas se envían al proveedor de IA que hayas configurado,
para generar la redacción sugerida.

## Versionado

1.5.0:
- Campo de coordinador con el nombre por dofecto
- Conteo consecutivo de numero de acta y la pososibilidad de editarlo
- Nombre del archivo de word con el formato que uso (numero de acta, fecha y nombre del estudinate)
- Se crea seccion "avanzado" que permite ver el prompt que se envia, y la respuesta que se recibe de la IA
- Se corrige la falta del am y pm en la hora en el word
- Se tiene en el campo de los nombres doble espacio (para firmas faciles)


1.0.0 
Aplicacion web que permite la sistematizacion de las actas de convivencia escolar, las cuales su redaccion se reaaliza con el llamado a una API de IA
