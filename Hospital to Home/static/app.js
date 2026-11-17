// Notifications polling (dashboard only)
// The server renders the latest notifications; start polling after the newest one
// so they are not added a second time.
let lastNotifFetch = null;

// Same categories as the notif_kind filter in app.py
const NOTIF_ICONS = {
  alert: "bi-exclamation-triangle-fill",
  discharge: "bi-house-check-fill",
  plan: "bi-clipboard2-check-fill",
};

function notifKind(title) {
  const t = (title || "").toLowerCase();
  if (t.includes("high")) return "alert";
  if (t.includes("discharged")) return "discharge";
  return "plan";
}

// Whole patient row opens the patient page
document.addEventListener("click", (e) => {
  const row = e.target.closest("tr[data-href]");
  if (row && !e.target.closest("a, button")) window.location = row.dataset.href;
});

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function fetchNotifications() {
  const list = document.getElementById("notif-list");
  if (!list) return;

  try {
    const url = lastNotifFetch
      ? `/api/notifications?since=${encodeURIComponent(lastNotifFetch)}`
      : "/api/notifications";

    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();

    if (Array.isArray(data) && data.length) {
      document.getElementById("notif-empty")?.remove();
      // API returns newest first; prepend oldest first so the newest ends up on top
      for (const n of [...data].reverse()) {
        // textContent (not innerHTML) so patient names/notes cannot inject markup
        const kind = notifKind(n.title);
        const div = el("div", `notif notif-${kind} notif-new`);
        const icon = el("div", "notif-icon");
        icon.append(el("i", `bi ${NOTIF_ICONS[kind]}`));
        const content = el("div", "flex-grow-1");
        content.append(
          el("div", "notif-title", n.title),
          el("div", "notif-body", n.body),
          el("div", "notif-meta", `just now • ${n.audience.replaceAll(",", ", ")}`),
        );
        div.append(icon, content);
        list.prepend(div);
      }
      lastNotifFetch = data[0].created_at;
    }
  } catch (e) {
    console.warn("Notification fetch failed:", e);
  }
}

window.addEventListener("load", () => {
  const list = document.getElementById("notif-list");
  if (!list) return;
  lastNotifFetch = list.dataset.latest || null;
  if (!lastNotifFetch) fetchNotifications();
  setInterval(fetchNotifications, 5000);
});

// Patient page handlers
document.addEventListener("DOMContentLoaded", () => {
  const pathname = window.location.pathname;
  const pathParts = pathname.split("/").filter(s => s);
  
  if (pathParts[0] !== "patient") return;
  const pid = pathParts[1];
  
  // 1) Vitals form
  const vitalsForm = document.getElementById("vitals-form");
  if (vitalsForm) {
    vitalsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(vitalsForm);
      const payload = {};
      for (const [k, v] of formData.entries()) {
        if (v !== "") payload[k] = v;
      }

      try {
        const res = await fetch(`/patient/${pid}/update_vitals`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to save vitals");
        const data = await res.json();

        const el = document.getElementById("vitals-status");
        if (el) {
          el.textContent = `✓ Saved — Risk ${data.risk_label} (${data.risk_score.toFixed(1)})`;
          setTimeout(() => (el.textContent = ""), 3000);
        }

        updateRiskChips(data.risk_label, data.risk_score);
        setTimeout(() => window.location.reload(), 1500);
      } catch (err) {
        alert("Could not save vitals. Please try again.");
        console.error(err);
      }
    });
  }

  // 2) Medications form
  const medsForm = document.getElementById("meds-form");
  if (medsForm) {
    medsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(medsForm);
      const payload = {};
      for (const [k, v] of formData.entries()) {
        payload[k] = v;
      }

      try {
        const res = await fetch(`/patient/${pid}/update_medications`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to save medications");
        const data = await res.json();

        const el = document.getElementById("meds-status");
        if (el) {
          el.textContent = `✓ Saved — Risk ${data.risk_label} (${data.risk_score.toFixed(1)})`;
          setTimeout(() => (el.textContent = ""), 3000);
        }

        updateRiskChips(data.risk_label, data.risk_score);
        setTimeout(() => window.location.reload(), 1500);
      } catch (err) {
        alert("Could not save medications. Please try again.");
        console.error(err);
      }
    });
  }

  // 3) Hospitalization form
  const hospForm = document.getElementById("hosp-form");
  if (hospForm) {
    hospForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(hospForm);
      const payload = {};
      for (const [k, v] of formData.entries()) {
        payload[k] = v;
      }

      try {
        const res = await fetch(`/patient/${pid}/update_hospitalization`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to save hospitalization data");
        const data = await res.json();

        const el = document.getElementById("hosp-status");
        if (el) {
          el.textContent = `✓ Saved — Risk ${data.risk_label} (${data.risk_score.toFixed(1)})`;
          setTimeout(() => (el.textContent = ""), 3000);
        }

        updateRiskChips(data.risk_label, data.risk_score);
        setTimeout(() => window.location.reload(), 1500);
      } catch (err) {
        alert("Could not save hospitalization data. Please try again.");
        console.error(err);
      }
    });
  }

  // 4) Care plan
  const planBtn = document.getElementById("save-plan");
  if (planBtn) {
    planBtn.addEventListener("click", async () => {
      const textarea = document.getElementById("plan-json");
      let payload = {};

      try {
        payload = JSON.parse(textarea.value || "{}");
      } catch (e) {
        alert("Invalid JSON in plan. Please fix and try again.");
        return;
      }

      try {
        const res = await fetch(`/patient/${pid}/update_plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to save plan");

        const el = document.getElementById("plan-status");
        if (el) {
          el.textContent = "✓ Saved & team notified";
          setTimeout(() => (el.textContent = ""), 3000);
        }
      } catch (err) {
        alert("Could not save plan. Please try again.");
        console.error(err);
      }
    });
  }
});

// Helper: Update risk chips
function updateRiskChips(label, score) {
  const chips = document.querySelectorAll(".risk-chip");
  chips.forEach((chip) => {
    chip.classList.remove("risk-LOW", "risk-MEDIUM", "risk-HIGH");
    chip.classList.add(`risk-${label}`);
    chip.textContent = `Risk: ${label} (${score.toFixed(1)})`;
  });
}