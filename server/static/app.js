const grid = document.getElementById("grid");
const statusEl = document.getElementById("status");
const lanEl = document.getElementById("lan");
const hoursEl = document.getElementById("hours");
const dayEl = document.getElementById("day");
const sourceEl = document.getElementById("source");
const nightStartEl = document.getElementById("nightStart");
const nightEndEl = document.getElementById("nightEnd");
let lastEvent = 0;

function fmt(ts) {
  return new Date(ts * 1000).toLocaleString("pt-PT");
}

function qs() {
  const day = dayEl.value;
  const source = sourceEl.value;
  const p = new URLSearchParams();
  if (day) p.set("day", day);
  if (source && source !== "all") p.set("source", source);
  const s = p.toString();
  return s ? `?${s}` : "";
}

function setStatus(connected, extra) {
  statusEl.textContent = connected
    ? extra || "ESP32 ligado · a vigiar a entrada"
    : "ESP32 desligado";
}

async function loadSettings() {
  const r = await fetch("/api/settings");
  const d = await r.json();
  hoursEl.value = d.retention_hours;
  nightStartEl.value = d.night_start;
  nightEndEl.value = d.night_end;
  lanEl.textContent = d.lan_url ? `Rede local: ${d.lan_url}` : "";
  setStatus(d.connected, d.connected ? `ESP32 ligado · ${d.count} foto(s)` : "");
}

async function loadPhotos() {
  const r = await fetch(`/api/photos${qs()}`);
  const d = await r.json();
  setStatus(d.connected);
  if (!d.photos.length) {
    grid.innerHTML = '<p class="empty">Sem fotos para este filtro.</p>';
    return;
  }
  grid.innerHTML = d.photos
    .map(
      (p) => `<article class="card">
        <a href="${p.url}" target="_blank"><img src="${p.url}" alt="${p.name}" /></a>
        <div class="meta">
          <span>${fmt(p.mtime)} · ${p.source}</span>
          <button data-del="${p.name}">Apagar</button>
        </div>
      </article>`
    )
    .join("");
}

async function poll() {
  try {
    const r = await fetch(`/api/events?after=${lastEvent}`);
    const d = await r.json();
    lastEvent = d.last || lastEvent;
    if (d.events.some((e) => ["photo", "cleared", "deleted", "exported"].includes(e.type))) {
      await loadPhotos();
    }
    setStatus(d.connected);
  } catch {
    statusEl.textContent = "Servidor indisponivel";
  }
}

document.getElementById("save").onclick = async () => {
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      retention_hours: Number(hoursEl.value),
      night_start: Number(nightStartEl.value),
      night_end: Number(nightEndEl.value),
    }),
  });
  await loadSettings();
};

document.getElementById("zip").onclick = () => {
  window.location = `/api/export.zip${qs()}`;
};

document.getElementById("desk").onclick = async () => {
  const day = dayEl.value;
  const url = day ? `/api/export-desktop?day=${day}` : "/api/export-desktop";
  const r = await fetch(url, { method: "POST" });
  if (!r.ok) {
    alert("Nao ha fotos para exportar.");
    return;
  }
  await loadPhotos();
};

document.getElementById("clear").onclick = async () => {
  if (!confirm("Apagar todas as fotos da interface?")) return;
  await fetch("/api/photos", { method: "DELETE" });
  await loadPhotos();
};

dayEl.onchange = loadPhotos;
sourceEl.onchange = loadPhotos;

grid.addEventListener("click", async (e) => {
  const name = e.target.dataset.del;
  if (!name) return;
  await fetch(`/api/photos/${encodeURIComponent(name)}`, { method: "DELETE" });
  await loadPhotos();
});

loadSettings().then(loadPhotos);
setInterval(poll, 1500);
