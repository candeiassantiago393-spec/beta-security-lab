const grid = document.getElementById("grid");
const statusEl = document.getElementById("status");
const hoursEl = document.getElementById("hours");
let lastEvent = 0;

function fmt(ts) {
  return new Date(ts * 1000).toLocaleString("pt-PT");
}

async function loadSettings() {
  const r = await fetch("/api/settings");
  const d = await r.json();
  hoursEl.value = d.retention_hours;
  statusEl.textContent = d.connected
    ? `ESP32 ligado · ${d.count} foto(s)`
    : "ESP32 desligado — confirma o cabo USB";
}

async function loadPhotos() {
  const r = await fetch("/api/photos");
  const d = await r.json();
  if (!d.photos.length) {
    grid.innerHTML = '<p class="empty">Ainda nao ha fotos. Passa a frente da câmara para testar o PIR.</p>';
    return;
  }
  grid.innerHTML = d.photos
    .map(
      (p) => `<article class="card">
        <a href="${p.url}" target="_blank"><img src="${p.url}" alt="${p.name}" /></a>
        <div class="meta">
          <span>${fmt(p.mtime)}</span>
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
    if (d.events.some((e) => e.type === "photo" || e.type === "cleared" || e.type === "deleted")) {
      await loadPhotos();
    }
    statusEl.textContent = d.connected
      ? "ESP32 ligado · a vigiar a entrada"
      : "ESP32 desligado — confirma o cabo USB";
  } catch {
    statusEl.textContent = "Servidor indisponivel";
  }
}

document.getElementById("save").onclick = async () => {
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ retention_hours: Number(hoursEl.value) }),
  });
  await loadSettings();
};

document.getElementById("clear").onclick = async () => {
  if (!confirm("Apagar todas as fotos?")) return;
  await fetch("/api/photos", { method: "DELETE" });
  await loadPhotos();
};

grid.addEventListener("click", async (e) => {
  const name = e.target.dataset.del;
  if (!name) return;
  await fetch(`/api/photos/${encodeURIComponent(name)}`, { method: "DELETE" });
  await loadPhotos();
});

loadSettings().then(loadPhotos);
setInterval(poll, 1500);
