const state = {
  actaId: null,
  personas: [],
  acciones: [],
};

function fechaHoyEsp() {
  const hoy = new Date();
  return hoy.toLocaleDateString("es-CO", {day: "numeric", month: "long", year: "numeric"});
}
document.getElementById("f-fecha").value = fechaHoyEsp();

// ---------- Navegación entre pestañas ----------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.view}`).classList.add("active");
    if (btn.dataset.view === "historial") cargarHistorial();
    if (btn.dataset.view === "config") cargarConfig();
  });
});

// ---------- Tabla de personas ----------
const TIPOS = [
  ["estudiante", "Estudiante"],
  ["acudiente", "Acudiente"],
  ["docente", "Docente"],
  ["directivo", "Directivo"],
  ["orientador", "Orientador(a)"],
  ["otro", "Otro"],
];

function filaPersonaHTML(p = {}) {
  const opciones = TIPOS.map(([v, l]) => `<option value="${v}" ${p.tipo === v ? "selected" : ""}>${l}</option>`).join("");
  return `<tr>
    <td><input type="text" class="p-nombre" value="${esc(p.nombre || "")}" placeholder="Nombre completo"></td>
    <td><select class="p-tipo">${opciones}</select></td>
    <td><input type="text" class="p-rol" value="${esc(p.rol_cargo || "")}" placeholder="Ej. Estudiante 902"></td>
    <td class="actions"><button class="btn danger small btn-quitar">✕</button></td>
  </tr>`;
}

function esc(s) {
  return (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function agregarPersona(p) {
  const tbody = document.querySelector("#tabla-personas tbody");
  tbody.insertAdjacentHTML("beforeend", filaPersonaHTML(p));
  const fila = tbody.lastElementChild;
  fila.querySelector(".btn-quitar").addEventListener("click", () => fila.remove());
}

document.getElementById("btn-add-persona").addEventListener("click", () => agregarPersona());

function leerPersonas() {
  return [...document.querySelectorAll("#tabla-personas tbody tr")].map(fila => ({
    nombre: fila.querySelector(".p-nombre").value.trim(),
    tipo: fila.querySelector(".p-tipo").value,
    rol_cargo: fila.querySelector(".p-rol").value.trim(),
  })).filter(p => p.nombre);
}

// filas iniciales
agregarPersona({tipo: "estudiante"});
agregarPersona({tipo: "acudiente"});

// ---------- Tabla de acciones (revisión IA) ----------
const CATEGORIAS = ["consensual", "restaurativa", "retributiva"];

function filaAccionHTML(a = {}) {
  const opciones = CATEGORIAS.map(c => `<option value="${c}" ${a.categoria === c ? "selected" : ""}>${c}</option>`).join("");
  return `<tr>
    <td><input type="text" class="a-desc" value="${esc(a.descripcion || "")}"></td>
    <td><select class="a-cat">${opciones}</select></td>
    <td><input type="text" class="a-art" value="${esc(a.articulo || "")}"></td>
    <td><input type="text" class="a-resp" value="${esc(a.responsable_sugerido || "")}"></td>
    <td class="actions"><button class="btn danger small btn-quitar">✕</button></td>
  </tr>`;
}

function agregarAccion(a) {
  const tbody = document.querySelector("#tabla-acciones tbody");
  tbody.insertAdjacentHTML("beforeend", filaAccionHTML(a));
  const fila = tbody.lastElementChild;
  fila.querySelector(".btn-quitar").addEventListener("click", () => fila.remove());
}

document.getElementById("btn-add-accion").addEventListener("click", () => agregarAccion());

function leerAcciones() {
  return [...document.querySelectorAll("#tabla-acciones tbody tr")].map(fila => ({
    descripcion: fila.querySelector(".a-desc").value.trim(),
    categoria: fila.querySelector(".a-cat").value,
    articulo: fila.querySelector(".a-art").value.trim(),
    responsable_sugerido: fila.querySelector(".a-resp").value.trim(),
  })).filter(a => a.descripcion);
}

// ---------- Analizar con IA ----------
function setStatus(elId, mensaje, tipo) {
  const el = document.getElementById(elId);
  el.innerHTML = mensaje ? `<div class="status-msg ${tipo}">${esc(mensaje)}</div>` : "";
}

document.getElementById("btn-analizar").addEventListener("click", async () => {
  const personas = leerPersonas();
  const descripcion = document.getElementById("f-descripcion").value.trim();
  if (!personas.length) { setStatus("analizar-status", "Agrega al menos una persona.", "error"); return; }
  if (!descripcion) { setStatus("analizar-status", "Escribe una descripción breve de la situación.", "error"); return; }

  setStatus("analizar-status", "Analizando con IA, ampliando la descripción y tipificando la situación...", "loading");
  document.getElementById("btn-analizar").disabled = true;
  try {
    const resp = await fetch("/api/analizar", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({personas, descripcion_breve: descripcion}),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Error desconocido");

    document.getElementById("card-revision").classList.remove("review-hidden");
    document.getElementById("r-tipo").value = (data.tipificacion && data.tipificacion.tipo) || "I";
    document.getElementById("r-articulo").value = (data.tipificacion && data.tipificacion.articulo) || "";
    document.getElementById("r-conducta").value = (data.tipificacion && data.tipificacion.conducta) || "";
    document.getElementById("r-justificacion").value = (data.tipificacion && data.tipificacion.justificacion) || "";
    document.getElementById("r-narrativa").value = data.narrativa_antecedentes || "";
    document.getElementById("r-acuerdos").value = data.acuerdos_texto || "";

    document.querySelector("#tabla-acciones tbody").innerHTML = "";
    (data.acciones_propuestas || []).forEach(agregarAccion);

    setStatus("analizar-status", "Listo. Revisa y ajusta lo que consideres antes de generar el acta.", "ok");
  } catch (err) {
    setStatus("analizar-status", err.message, "error");
  } finally {
    document.getElementById("btn-analizar").disabled = false;
  }
});

// ---------- Guardar / Generar ----------
function construirPayload(estado) {
  return {
    numero_acta: state.numeroActa || null,
    fecha: document.getElementById("f-fecha").value,
    hora_inicio: document.getElementById("f-hora-inicio").value,
    hora_fin: document.getElementById("f-hora-fin").value,
    lugar: document.getElementById("f-lugar").value,
    elaborada_por: document.getElementById("f-elaborada-por").value,
    personas: leerPersonas(),
    descripcion_breve: document.getElementById("f-descripcion").value,
    tipificacion: {
      tipo: document.getElementById("r-tipo").value,
      articulo: document.getElementById("r-articulo").value,
      conducta: document.getElementById("r-conducta").value,
      justificacion: document.getElementById("r-justificacion").value,
    },
    narrativa_antecedentes: document.getElementById("r-narrativa").value,
    acciones: leerAcciones(),
    acuerdos_texto: document.getElementById("r-acuerdos").value,
    proxima_reunion: {
      fecha: document.getElementById("pr-fecha").value,
      hora: document.getElementById("pr-hora").value,
      lugar: document.getElementById("pr-lugar").value,
    },
    estado,
  };
}

async function guardarActa(estado) {
  const payload = construirPayload(estado);
  if (!payload.fecha) throw new Error("Selecciona la fecha del acta.");
  if (!payload.personas.length) throw new Error("Agrega al menos una persona.");

  const url = state.actaId ? `/api/actas/${state.actaId}` : "/api/actas";
  const method = state.actaId ? "PUT" : "POST";
  const resp = await fetch(url, {
    method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "No se pudo guardar el acta.");
  state.actaId = data.id;
  state.numeroActa = data.numero_acta;
  return data;
}

document.getElementById("btn-guardar-borrador").addEventListener("click", async () => {
  try {
    const acta = await guardarActa("borrador");
    setStatus("guardar-status", `Borrador guardado (Acta No. ${acta.numero_acta}).`, "ok");
  } catch (err) {
    setStatus("guardar-status", err.message, "error");
  }
});

document.getElementById("btn-generar-word").addEventListener("click", async () => {
  try {
    setStatus("guardar-status", "Guardando y generando el documento Word...", "loading");
    const acta = await guardarActa("final");
    const resp = await fetch(`/api/actas/${acta.id}/generar-docx`, {method: "POST"});
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "No se pudo generar el documento.");
    setStatus("guardar-status", `Documento generado (Acta No. ${acta.numero_acta}). Descargando...`, "ok");
    window.open(data.url, "_blank");
  } catch (err) {
    setStatus("guardar-status", err.message, "error");
  }
});

// ---------- Historial ----------
async function cargarHistorial() {
  const q = document.getElementById("h-buscar").value.trim();
  const resp = await fetch(`/api/actas${q ? "?q=" + encodeURIComponent(q) : ""}`);
  const actas = await resp.json();
  const tbody = document.getElementById("historial-body");
  tbody.innerHTML = "";
  if (!actas.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#889">Sin actas registradas todavía.</td></tr>`;
    return;
  }
  for (const acta of actas) {
    const nombres = (acta.personas || []).map(p => p.nombre).join(", ");
    const tipo = acta.tipificacion ? acta.tipificacion.tipo : "-";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${acta.numero_acta}</td>
      <td>${esc(acta.fecha)}</td>
      <td>${esc(nombres)}</td>
      <td>${tipo !== "-" ? `<span class="tag tipo-${tipo}">Tipo ${tipo}</span>` : "-"}</td>
      <td><span class="badge-estado ${acta.estado}">${acta.estado}</span></td>
      <td>
        <button class="btn secondary small btn-abrir">Abrir</button>
        ${acta.archivo_path ? `<a class="btn small" style="text-decoration:none;display:inline-block;margin-left:6px" href="/api/actas/${acta.id}/descargar">Descargar</a>` : ""}
      </td>`;
    tr.querySelector(".btn-abrir").addEventListener("click", () => abrirActa(acta.id));
    tbody.appendChild(tr);
  }
}

document.getElementById("btn-buscar").addEventListener("click", cargarHistorial);

async function abrirActa(id) {
  const resp = await fetch(`/api/actas/${id}`);
  const acta = await resp.json();
  state.actaId = acta.id;
  state.numeroActa = acta.numero_acta;

  document.getElementById("f-fecha").value = acta.fecha || "";
  document.getElementById("f-hora-inicio").value = acta.hora_inicio || "";
  document.getElementById("f-hora-fin").value = acta.hora_fin || "";
  document.getElementById("f-lugar").value = acta.lugar || "Coordinación";
  document.getElementById("f-elaborada-por").value = acta.elaborada_por || "";
  document.getElementById("f-descripcion").value = acta.descripcion_breve || "";

  document.querySelector("#tabla-personas tbody").innerHTML = "";
  (acta.personas || []).forEach(agregarPersona);

  if (acta.tipificacion || acta.narrativa_antecedentes) {
    document.getElementById("card-revision").classList.remove("review-hidden");
    document.getElementById("r-tipo").value = (acta.tipificacion && acta.tipificacion.tipo) || "I";
    document.getElementById("r-articulo").value = (acta.tipificacion && acta.tipificacion.articulo) || "";
    document.getElementById("r-conducta").value = (acta.tipificacion && acta.tipificacion.conducta) || "";
    document.getElementById("r-justificacion").value = (acta.tipificacion && acta.tipificacion.justificacion) || "";
    document.getElementById("r-narrativa").value = acta.narrativa_antecedentes || "";
    document.getElementById("r-acuerdos").value = acta.acuerdos_texto || "";
    document.querySelector("#tabla-acciones tbody").innerHTML = "";
    (acta.acciones || []).forEach(agregarAccion);
  }
  if (acta.proxima_reunion) {
    document.getElementById("pr-fecha").value = acta.proxima_reunion.fecha || "";
    document.getElementById("pr-hora").value = acta.proxima_reunion.hora || "";
    document.getElementById("pr-lugar").value = acta.proxima_reunion.lugar || "";
  }

  document.querySelector('.tab-btn[data-view="nueva"]').click();
  setStatus("guardar-status", `Editando Acta No. ${acta.numero_acta}.`, "ok");
}

// ---------- Configuración del proveedor de IA ----------
function providerCardHTML(key, info, providerActivo) {
  const activo = key === providerActivo;
  const estadoTag = info.configured
    ? `<span class="tag-configurado">Configurada${info.from_env ? " (variable de entorno)" : ""}</span>`
    : `<span class="tag-sin-configurar">Sin configurar</span>`;
  return `
    <div class="provider-card ${activo ? "activo" : ""}" data-provider="${key}">
      <div class="provider-header">
        <label class="radio">
          <input type="radio" name="provider-activo" value="${key}" ${activo ? "checked" : ""}>
          ${esc(info.label)}
        </label>
        <div>
          ${estadoTag}
          <a class="provider-help" href="${info.help_url}" target="_blank" rel="noopener">Obtener API key ↗</a>
        </div>
      </div>
      <div class="provider-fields">
        <div class="field">
          <label>API key</label>
          <input type="password" class="cfg-key" placeholder="${info.key_preview ? "Dejar en blanco para conservar la actual" : "Pega aquí tu API key"}">
          ${info.key_preview ? `<div class="key-preview">Actual: ${esc(info.key_preview)}</div>` : ""}
        </div>
        <div class="field">
          <label>Modelo</label>
          <input type="text" class="cfg-model" value="${esc(info.model)}" placeholder="${esc(info.default_model)}">
          ${info.model !== info.default_model
            ? `<div class="key-preview">Sugerido: ${esc(info.default_model)} — <button type="button" class="link btn-restablecer-modelo">usar este</button></div>`
            : ""}
        </div>
      </div>
      <div class="actions-bar" style="margin-top:10px">
        <button class="btn small btn-guardar-provider">Guardar</button>
        ${info.configured ? `<button class="btn danger small btn-borrar-provider">Quitar API key</button>` : ""}
      </div>
    </div>`;
}

async function cargarConfig() {
  const contenedor = document.getElementById("config-lista");
  contenedor.innerHTML = "<p class='hint'>Cargando configuración...</p>";
  const resp = await fetch("/api/config");
  const data = await resp.json();
  renderConfig(data);
}

function renderConfig(data) {
  const contenedor = document.getElementById("config-lista");
  contenedor.innerHTML = Object.entries(data.providers)
    .map(([key, info]) => providerCardHTML(key, info, data.provider))
    .join("");

  contenedor.querySelectorAll(".provider-card").forEach(card => {
    const key = card.dataset.provider;

    card.querySelector('input[name="provider-activo"]').addEventListener("change", async () => {
      const resp = await fetch("/api/config", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({provider: key}),
      });
      renderConfig(await resp.json());
    });

    card.querySelector(".btn-guardar-provider").addEventListener("click", async () => {
      const apiKey = card.querySelector(".cfg-key").value.trim();
      const model = card.querySelector(".cfg-model").value.trim();
      const resp = await fetch("/api/config", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({provider: key, api_key: apiKey || null, model: model || null}),
      });
      const data = await resp.json();
      if (!resp.ok) { alert(data.detail || "No se pudo guardar la configuración."); return; }
      renderConfig(data);
    });

    const btnBorrar = card.querySelector(".btn-borrar-provider");
    if (btnBorrar) {
      btnBorrar.addEventListener("click", async () => {
        if (!confirm("¿Quitar la API key guardada para este proveedor?")) return;
        const resp = await fetch(`/api/config/${key}`, {method: "DELETE"});
        renderConfig(await resp.json());
      });
    }

    const btnRestablecer = card.querySelector(".btn-restablecer-modelo");
    if (btnRestablecer) {
      btnRestablecer.addEventListener("click", () => {
        card.querySelector(".cfg-model").value = card.querySelector(".cfg-model").placeholder;
      });
    }
  });
}
