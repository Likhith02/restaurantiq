/* RestaurantIQ frontend — no frameworks, just clean JS. */

const $ = (id) => document.getElementById(id);
let TOKEN = localStorage.getItem("riq_token");
let CUR = "₹";

/* ---------- tiny helpers ---------- */

function money(n) {
  const locale = CUR === "₹" ? "en-IN" : "en-US";
  return CUR + Math.round(n).toLocaleString(locale);
}

function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), 2600);
}

async function api(path, body) {
  const opts = {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
  };
  if (TOKEN) opts.headers["Authorization"] = "Bearer " + TOKEN;
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch("/api" + path, opts);
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) { logout(); throw new Error("Please log in again."); }
  if (!res.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
  return data;
}

function show(screen) {
  ["screen-login", "screen-setup", "screen-app"].forEach((s) =>
    $(s).classList.toggle("hidden", s !== screen)
  );
}

function logout() {
  TOKEN = null;
  localStorage.removeItem("riq_token");
  $("login-step-phone").classList.remove("hidden");
  $("login-step-code").classList.add("hidden");
  show("screen-login");
}

/* ---------- login ---------- */

$("btn-get-code").onclick = async () => {
  const phone = $("phone").value;
  try {
    const r = await api("/auth/request-otp", { phone });
    $("login-step-phone").classList.add("hidden");
    $("login-step-code").classList.remove("hidden");
    $("otp-hint").textContent =
      `Demo mode — your code is ${r.demo_otp}. In the real app this arrives as an SMS.`;
    $("otp").focus();
  } catch (e) { toast(e.message); }
};

$("btn-back").onclick = () => {
  $("login-step-phone").classList.remove("hidden");
  $("login-step-code").classList.add("hidden");
};

$("btn-verify").onclick = async () => {
  try {
    const r = await api("/auth/verify-otp", { phone: $("phone").value, code: $("otp").value });
    TOKEN = r.token;
    localStorage.setItem("riq_token", TOKEN);
    if (r.needs_setup) show("screen-setup");
    else enterApp();
  } catch (e) { toast(e.message); }
};

$("btn-demo").onclick = async () => {
  try {
    const r = await api("/auth/demo", {});
    TOKEN = r.token;
    localStorage.setItem("riq_token", TOKEN);
    enterApp();
  } catch (e) { toast(e.message); }
};

/* ---------- setup ---------- */

document.querySelectorAll("#setup-currency .pill").forEach((p) => {
  p.onclick = () => {
    document.querySelectorAll("#setup-currency .pill").forEach((x) => x.classList.remove("selected"));
    p.classList.add("selected");
  };
});

$("btn-setup-done").onclick = async () => {
  const cur = document.querySelector("#setup-currency .pill.selected").dataset.cur;
  try {
    await api("/setup", {
      name: $("setup-name").value,
      rtype: $("setup-type").value,
      seats: parseInt($("setup-seats").value) || null,
      currency: cur,
    });
    enterApp();
  } catch (e) { toast(e.message); }
};

/* ---------- app shell ---------- */

document.querySelectorAll(".nav-btn").forEach((b) => {
  b.onclick = () => switchTab(b.dataset.tab);
});

function switchTab(tab) {
  document.querySelectorAll(".nav-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === tab)
  );
  ["home", "add", "ask"].forEach((t) =>
    $("tab-" + t).classList.toggle("hidden", t !== tab)
  );
  if (tab === "home") loadDashboard();
  if (tab === "add") $("e-date").value = new Date().toISOString().slice(0, 10);
}

$("btn-logout").onclick = logout;
$("btn-first-entry").onclick = () => switchTab("add");

async function enterApp() {
  show("screen-app");
  switchTab("home");
}

/* ---------- home / dashboard ---------- */

async function loadDashboard() {
  let d;
  try { d = await api("/dashboard"); } catch (e) { toast(e.message); return; }

  CUR = d.restaurant.currency || "₹";
  $("rest-name").textContent = d.restaurant.name || "Your restaurant";
  const hour = new Date().getHours();
  $("greet").textContent = hour < 12 ? "Good morning ☀️" : hour < 17 ? "Good afternoon 👋" : "Good evening 🌙";

  const hasData = d.n_entries > 0;
  $("home-empty").classList.toggle("hidden", hasData);
  $("home-content").classList.toggle("hidden", !hasData);
  if (!hasData) return;

  // hero number = most recent day's sales
  const latest = d.latest;
  const latestDate = new Date(latest.date + "T00:00:00");
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = Math.round((today - latestDate) / 86400000);
  $("hero-label").textContent =
    diff === 0 ? "Today's sales" : diff === 1 ? "Yesterday's sales" :
    latestDate.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" }) + " — sales";
  $("hero-number").textContent = money(latest.sales);

  let sub = "";
  if (d.week.days >= 5) {
    sub = `This week so far: ${money(d.week.total)}`;
    if (d.week.change_pct !== null) {
      const up = d.week.change_pct >= 0;
      sub += ` · <span class="${up ? "up" : "down"}">${up ? "▲" : "▼"} ${Math.abs(d.week.change_pct).toFixed(0)}% vs last week</span>`;
    }
  } else {
    sub = `${d.n_entries} day${d.n_entries === 1 ? "" : "s"} recorded — keep going!`;
  }
  $("hero-sub").innerHTML = sub;

  // traffic lights
  $("lights").innerHTML = d.lights.map((l) => `
    <div class="light ${l.level}">
      <div class="l-label"><span class="dot"></span>${l.label}</div>
      <div class="l-line">${l.line}</div>
    </div>`).join("");

  // insights: first one is the headline, rest below the chart
  const render = (i) => `
    <div class="insight ${i.level}">
      <div class="i-title">${i.title}</div>
      <div class="i-detail">${i.detail}</div>
      ${i.action ? `<div class="i-action">${i.action}</div>` : ""}
    </div>`;
  $("top-insight").innerHTML = d.insights.length ? render(d.insights[0]) : "";
  $("more-insights").innerHTML = d.insights.slice(1).map(render).join("");

  // 14-day bar chart
  const max = Math.max(...d.chart.map((c) => c.sales), 1);
  $("chart").innerHTML = d.chart.map((c) => {
    const day = new Date(c.date + "T00:00:00");
    const wd = day.getDay(); // 0 Sun, 6 Sat
    const label = day.toLocaleDateString(undefined, { weekday: "narrow" });
    const h = Math.max(2, (c.sales / max) * 100);
    return `<div class="bar-wrap" title="${c.date}: ${money(c.sales)}">
      <div class="bar ${wd === 0 || wd === 6 ? "weekend" : ""}" style="height:${h}%"></div>
      <div class="bar-day">${label}</div>
    </div>`;
  }).join("");
}

/* ---------- add entry ---------- */

$("btn-save-entry").onclick = async () => {
  const sales = parseFloat($("e-sales").value);
  if (isNaN(sales)) { toast("Please enter how much you earned."); return; }
  const num = (id) => { const v = parseFloat($(id).value); return isNaN(v) ? null : v; };
  try {
    await api("/entries", {
      date: $("e-date").value || null,
      sales,
      customers: num("e-customers"),
      staff_count: num("e-staff"),
      staff_cost: num("e-staffcost"),
      food_cost: num("e-foodcost"),
    });
    ["e-sales", "e-customers", "e-staff", "e-staffcost", "e-foodcost"].forEach((id) => ($(id).value = ""));
    toast("Saved! 🎉");
    switchTab("home");
  } catch (e) { toast(e.message); }
};

/* ---------- ask ---------- */

function addMsg(text, who) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  $("chat").appendChild(div);
  div.scrollIntoView({ behavior: "smooth", block: "end" });
  return div;
}

async function ask(question) {
  if (!question.trim()) return;
  addMsg(question, "user");
  $("ask-input").value = "";
  const thinking = addMsg("Thinking…", "bot");
  thinking.classList.add("thinking");
  try {
    const r = await api("/ask", { question });
    thinking.classList.remove("thinking");
    thinking.textContent = r.answer;
  } catch (e) {
    thinking.classList.remove("thinking");
    thinking.textContent = e.message;
  }
  thinking.scrollIntoView({ behavior: "smooth", block: "end" });
}

$("btn-ask").onclick = () => ask($("ask-input").value);
$("ask-input").addEventListener("keydown", (e) => { if (e.key === "Enter") ask($("ask-input").value); });
document.querySelectorAll(".chip").forEach((c) => (c.onclick = () => ask(c.textContent)));

/* ---------- boot ---------- */

if (TOKEN) {
  api("/me")
    .then((me) => {
      CUR = me.currency || "₹";
      if (me.name) enterApp();
      else show("screen-setup");
    })
    .catch(() => logout());
} else {
  show("screen-login");
}
