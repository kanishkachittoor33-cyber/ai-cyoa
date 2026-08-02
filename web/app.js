let sessionId = null;
let adventureId = null;
let previewId = null;
let lastNarrative = "";

const $ = (id) => document.getElementById(id);

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function showLobby() {
  $("lobby").hidden = false;
  $("play").hidden = true;
  $("rail-play-tools").hidden = true;
  sessionId = null;
  adventureId = null;
  refreshAdventureList();
}

function showPlay() {
  $("lobby").hidden = true;
  $("play").hidden = false;
  $("rail-play-tools").hidden = false;
}

function setBar(id, value) {
  $(id).style.width = `${Math.max(0, Math.min(100, value))}%`;
}

function statusLabel(status) {
  if (status === "won") return "won";
  if (status === "lost") return "lost";
  return "in progress";
}

async function refreshAdventureList() {
  let data;
  try {
    data = await api("/api/adventures");
  } catch {
    return;
  }

  const list = $("adventure-list");
  list.innerHTML = "";
  const open = data.open || [];
  const saved = data.saved || [];
  const all = [
    ...open.map((a) => ({ ...a, open: true })),
    ...saved.map((a) => ({ ...a, open: false })),
  ];

  $("adventure-empty").hidden = all.length > 0;

  for (const adv of all) {
    const row = document.createElement("div");
    row.className = "adv-tab" + (adv.id === adventureId ? " active" : "");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "adv-tab-main";
    btn.innerHTML = `
      <span class="adv-title">${escapeHtml(adv.title)}</span>
      <span class="adv-meta">t=${adv.t} · ${escapeHtml(adv.area_name)} · ${statusLabel(adv.status)}</span>
    `;
    btn.addEventListener("click", () => switchAdventure(adv.id));

    const del = document.createElement("button");
    del.type = "button";
    del.className = "adv-tab-del";
    del.title = "Remove";
    del.textContent = "×";
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      removeAdventure(adv.id);
    });

    row.appendChild(btn);
    row.appendChild(del);
    list.appendChild(row);
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderPreview(data) {
  previewId = data.preview_id;
  $("preview").hidden = false;
  $("preview-title").textContent = data.title;
  $("preview-premise").textContent = data.premise;
  $("preview-objective").textContent =
    data.objective || "Survive and finish the goal.";
  $("preview-source").textContent =
    data.source === "llm" ? "AI-generated setting" : "Generated setting";
}

function enterAdventure(data) {
  sessionId = data.session_id;
  adventureId = data.adventure?.id || data.adventure_id || null;
  lastNarrative = "";
  showPlay();
  render(data);
  refreshAdventureList();
}

function render(data, message) {
  const { area, state, actions, premise, title, objective } = data;
  const c = state.character;

  if (data.adventure?.id) adventureId = data.adventure.id;

  document.title = title || "Adventure";
  $("brand-title").textContent = title || "Adventure";
  $("premise").textContent = premise || "";
  if (objective) {
    $("objective-line").hidden = false;
    $("objective-line").textContent = `Objective: ${objective}`;
  } else {
    $("objective-line").hidden = true;
  }

  $("time").textContent = `t = ${state.t}`;
  $("area-name").textContent = area.name;
  $("area-desc").textContent = area.description;

  const narrative = message || state.log[state.log.length - 1] || "";
  if (narrative !== lastNarrative) {
    const el = $("narrative");
    el.style.animation = "none";
    el.offsetHeight;
    el.style.animation = "";
    el.textContent = narrative;
    lastNarrative = narrative;
  }

  $("health-val").textContent = c.health;
  $("satiation-val").textContent = c.satiation;
  $("energy-val").textContent = c.energy;
  setBar("health-bar", c.health);
  setBar("satiation-bar", c.satiation);
  setBar("energy-bar", c.energy);

  const satBand = $("satiation-band");
  satBand.textContent = c.is_hungry ? "Hungry" : "Satiated";
  satBand.classList.toggle("warn", c.is_hungry);

  const enBand = $("energy-band");
  enBand.textContent = c.is_fatigued ? "Fatigued" : "Energized";
  enBand.classList.toggle("warn", c.is_fatigued);

  const items = c.items || [];
  $("items").textContent = items.length
    ? items.map((i) => i.name).join(" · ")
    : "Empty";

  const pill = $("status-pill");
  pill.className = "pill";
  if (state.status === "won") {
    pill.textContent = "free";
    pill.classList.add("won");
  } else if (state.status === "lost") {
    pill.textContent = "fallen";
    pill.classList.add("lost");
  } else {
    pill.textContent = "exploring";
  }

  $("restart").classList.toggle("ended", state.status !== "playing");

  const list = $("actions");
  list.innerHTML = "";
  if (state.status !== "playing") {
    refreshAdventureList();
    return;
  }

  for (const action of actions) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "action";
    btn.disabled = !action.available;

    const label = document.createElement("span");
    label.textContent = action.label;
    btn.appendChild(label);

    const hints = [];
    if (action.energy_cost) hints.push(`−${action.energy_cost} energy`);
    if (
      action.show_chance &&
      action.resolved_chance != null &&
      action.available
    ) {
      hints.push(`${Math.round(action.resolved_chance * 100)}% success`);
    }
    if (action.kind === "transition" && action.gate?.status === "closed") {
      hints.push("closed path");
    }
    if (!action.available && action.blocked_reason) {
      hints.push(action.blocked_reason);
    }
    if (hints.length) {
      const hint = document.createElement("span");
      hint.className = "hint";
      hint.innerHTML = hints
        .map((h, i) =>
          i === 0 && action.energy_cost
            ? `<span class="cost">${h}</span>`
            : h
        )
        .join(" · ");
      btn.appendChild(hint);
    }

    btn.addEventListener("click", () => act(action.id));
    list.appendChild(btn);
  }

  refreshAdventureList();
}

async function startClassic() {
  const data = await api("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario: "lost_in_the_woods" }),
  });
  enterAdventure(data);
}

async function generateSetting() {
  const status = $("generate-status");
  const btn = $("btn-generate");
  status.hidden = false;
  status.textContent = "Inventing a setting…";
  btn.disabled = true;
  try {
    const data = await api("/api/generate", { method: "POST", body: "{}" });
    status.hidden = true;
    renderPreview(data);
  } catch (err) {
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

async function acceptPreview() {
  if (!previewId) return;
  const data = await api("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preview_id: previewId }),
  });
  enterAdventure(data);
}

async function act(actionId) {
  const data = await api("/api/act", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action_id: actionId }),
  });
  render(data, data.message);
}

async function switchAdventure(id) {
  if (id === adventureId && sessionId) {
    showPlay();
    return;
  }
  const data = await api("/api/adventures/switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adventure_id: id }),
  });
  enterAdventure(data);
}

async function removeAdventure(id) {
  await api("/api/adventures/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adventure_id: id }),
  });
  if (id === adventureId) showLobby();
  else refreshAdventureList();
}

async function saveProgress() {
  if (!sessionId) return;
  const status = $("save-status");
  status.hidden = false;
  status.textContent = "Saving…";
  try {
    const data = await api("/api/adventures/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    adventureId = data.adventure.id;
    status.textContent = "Saved";
    refreshAdventureList();
    setTimeout(() => {
      status.hidden = true;
    }, 1200);
  } catch (err) {
    status.textContent = err.message;
  }
}

$("btn-woods").addEventListener("click", () => {
  startClassic().catch((err) => {
    $("generate-status").hidden = false;
    $("generate-status").textContent = err.message;
  });
});

$("btn-lobby").addEventListener("click", () => {
  showLobby();
  $("preview").hidden = true;
  previewId = null;
});

$("btn-generate").addEventListener("click", () => {
  generateSetting().catch(() => {});
});

$("btn-reroll").addEventListener("click", () => {
  generateSetting().catch(() => {});
});

$("btn-accept").addEventListener("click", () => {
  acceptPreview().catch((err) => {
    $("generate-status").hidden = false;
    $("generate-status").textContent = err.message;
  });
});

$("btn-save").addEventListener("click", () => {
  saveProgress().catch(() => {});
});

$("restart").addEventListener("click", () => {
  showLobby();
  $("preview").hidden = true;
  previewId = null;
});

showLobby();
