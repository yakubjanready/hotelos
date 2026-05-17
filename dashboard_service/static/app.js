/* HotelOS panel — frontend mantiq.
 *
 * Hodisaga asoslangan kod uslubi (Tasl-2.4 misoli):
 *   - WebSocket xabarlari `wsMsgHandlers` xaritasi orqali tarqatiladi.
 *   - Foydalanuvchi harakatlari (login, logout) DOM hodisa tinglovchilar bilan ulanadi.
 */

"use strict";

const TOKEN_KEY = "hotelos.token";
let socket = null;
let state = { rooms: [], orders: [], issues: [], guests_by_room: {} };
const eventStream = [];

// === DOM yordamchilari ===
const $ = (id) => document.getElementById(id);

const STATUS_CLASS = {
  clean: "status-clean",
  occupied: "status-occupied",
  dirty: "status-dirty",
  cleaning: "status-cleaning",
  maintenance: "status-maintenance",
};

const STATUS_LABEL = {
  clean: "Toza",
  occupied: "Band",
  dirty: "Iflos",
  cleaning: "Tozalanmoqda",
  maintenance: "Texnik",
};

// === Autentifikatsiya oqimi ===
$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = $("username").value.trim();
  const password = $("password").value;
  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Login muvaffaqiyatsiz");
    const { token } = await res.json();
    localStorage.setItem(TOKEN_KEY, token);
    enterDashboard(token);
  } catch (err) {
    const el = $("login-error");
    el.textContent = err.message;
    el.classList.remove("hidden");
  }
});

$("logout-btn").addEventListener("click", () => {
  localStorage.removeItem(TOKEN_KEY);
  if (socket) socket.close();
  $("dashboard").classList.add("hidden");
  $("login-screen").classList.remove("hidden");
});

function enterDashboard(token) {
  $("login-screen").classList.add("hidden");
  $("dashboard").classList.remove("hidden");
  connectWebSocket(token);
}

function connectWebSocket(token) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`);

  socket.addEventListener("open", () => updateConnStatus(true));
  socket.addEventListener("close", () => updateConnStatus(false));
  socket.addEventListener("error", () => updateConnStatus(false));
  socket.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    handleMessage(msg);
  });
}

function updateConnStatus(connected) {
  const dot = $("conn-dot");
  const text = $("conn-text");
  if (connected) {
    dot.classList.remove("bg-red-500");
    dot.classList.add("bg-emerald-500");
    text.textContent = "Ulangan";
  } else {
    dot.classList.remove("bg-emerald-500");
    dot.classList.add("bg-red-500");
    text.textContent = "Uzilgan";
  }
}

// === WebSocket xabar tarqatuvchi (Tasl-2.4 misoli) ===
const wsMsgHandlers = {
  initial_state: (p) => { state = p; renderAll(); },
  "room.occupied": (p) => { mergeRoom(p.room_number, "occupied"); state.guests_by_room[p.room_number] = { name: p.guest_name }; renderAll(); },
  "room.vacated": (p) => { mergeRoom(p.room_number, "dirty"); delete state.guests_by_room[p.room_number]; renderAll(); },
  "room.cleaning_started": (p) => { mergeRoom(p.room_number, "cleaning"); renderAll(); },
  "room.cleaned": (p) => { mergeRoom(p.room_number, "clean"); renderAll(); },
  "order.received": (p) => upsertOrder(p),
  "order.preparing": (p) => upsertOrder(p),
  "order.delivering": (p) => upsertOrder(p),
  "order.delivered": (p) => { state.orders = state.orders.filter(o => o.order_id !== p.order_id); renderAll(); },
  "issue.reported": (p) => upsertIssue(p),
  "issue.assigned": (p) => upsertIssue(p),
  "issue.resolved": (p) => { state.issues = state.issues.filter(i => i.issue_id !== p.issue_id); renderAll(); },
};

function handleMessage(msg) {
  pushEventStream(msg.type, msg.payload);
  const handler = wsMsgHandlers[msg.type];
  if (handler) handler(msg.payload);
}

function mergeRoom(number, status) {
  const idx = state.rooms.findIndex(r => r.number === Number(number));
  if (idx >= 0) state.rooms[idx].status = status;
}

function upsertOrder(payload) {
  const idx = state.orders.findIndex(o => o.order_id === payload.order_id);
  if (idx >= 0) state.orders[idx] = { ...state.orders[idx], ...payload };
  else state.orders.push({ ...payload });
  renderAll();
}

function upsertIssue(payload) {
  const idx = state.issues.findIndex(i => i.issue_id === payload.issue_id);
  if (idx >= 0) state.issues[idx] = { ...state.issues[idx], ...payload };
  else state.issues.push({ ...payload });
  renderAll();
}

function pushEventStream(type, payload) {
  const ts = new Date().toLocaleTimeString();
  const line = `[${ts}] ${type} :: xona ${payload.room_number || "?"}`;
  eventStream.unshift(line);
  if (eventStream.length > 20) eventStream.pop();
  const ul = $("event-stream");
  ul.innerHTML = eventStream.map(l => `<li>${l}</li>`).join("");
  $("last-event").textContent = line;
}

// === Render ===
function renderAll() {
  renderStats();
  renderRooms();
  renderOrders();
  renderIssues();
}

function renderStats() {
  const total = state.rooms.length;
  const byStatus = state.rooms.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {});
  $("stat-total").textContent = total;
  $("stat-clean").textContent = byStatus.clean || 0;
  $("stat-occupied").textContent = byStatus.occupied || 0;
  $("stat-dirty").textContent = (byStatus.dirty || 0) + (byStatus.cleaning || 0);
  $("stat-issues").textContent = state.issues.length;
}

function renderRooms() {
  const grouped = {};
  state.rooms.forEach(r => {
    grouped[r.floor] = grouped[r.floor] || [];
    grouped[r.floor].push(r);
  });
  const html = Object.keys(grouped).sort((a, b) => b - a).map(floor => {
    const cards = grouped[floor].sort((a, b) => a.number - b.number).map(r => {
      const cls = STATUS_CLASS[r.status] || "bg-slate-600";
      const guest = state.guests_by_room[r.number];
      const tooltip = `Xona ${r.number} | ${STATUS_LABEL[r.status]}${guest ? " | " + guest.name : ""}`;
      return `<div class="room-card ${cls}" title="${tooltip}">
        <span class="font-bold">${r.number}</span>
        <span class="text-[10px] opacity-80">${(r.room_type || "")[0]?.toUpperCase() || ""}</span>
      </div>`;
    }).join("");
    return `<div><div class="floor-label">${floor}-qavat</div><div class="flex flex-wrap">${cards}</div></div>`;
  }).join("");
  $("rooms-grid").innerHTML = html;
}

function renderOrders() {
  const list = $("orders-list");
  if (!state.orders.length) {
    list.innerHTML = `<p class="text-slate-500 italic">Hozircha buyurtma yo'q</p>`;
    return;
  }
  list.innerHTML = state.orders.map(o => `
    <div class="bg-slate-700 rounded p-2 flex justify-between">
      <div>
        <div class="font-mono text-xs text-slate-400">${o.order_id}</div>
        <div>Xona ${o.room_number} · <span class="text-emerald-300">${o.status}</span></div>
      </div>
      <div class="font-semibold">${o.total ?? ""}</div>
    </div>
  `).join("");
}

function renderIssues() {
  const list = $("issues-list");
  if (!state.issues.length) {
    list.innerHTML = `<p class="text-slate-500 italic">Ochiq muammo yo'q</p>`;
    return;
  }
  list.innerHTML = state.issues.map(i => `
    <div class="bg-slate-700 rounded p-2 urgency-${i.urgency || 'normal'}">
      <div class="flex justify-between">
        <span class="font-semibold">Xona ${i.room_number}</span>
        <span class="text-xs uppercase">${i.urgency || ""}</span>
      </div>
      <div class="text-slate-300">${i.description || ""}</div>
      ${i.technician ? `<div class="text-xs text-slate-400">Texnik: ${i.technician}</div>` : ""}
    </div>
  `).join("");
}

// === Avtomatik kirish (saqlangan token mavjud bo'lsa) ===
window.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) enterDashboard(saved);
});
