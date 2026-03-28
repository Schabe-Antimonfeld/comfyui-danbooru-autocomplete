const CATEGORY_COLORS = {
  0: "#4e9af1",
  1: "#f1964e",
  3: "#c84ef1",
  4: "#4ef17a",
  5: "#f14e4e",
};
const CATEGORY_NAMES = {
  0: "general", 1: "artist", 3: "copyright", 4: "character", 5: "meta",
};

const ONLINE_API = "/danbooru-autocomplete/online-tags";
const LOCAL_API = "/danbooru-autocomplete/tags";
const ONLINE_FAIL_THRESHOLD = 3;
const ONLINE_RETRY_MS = 60_000;

let dropdownEl = null;
let activeTextarea = null;
let abortCtrl = null;
let selectedIdx = -1;
let results = [];
let debounceTimer = null;
const patchedSet = new WeakSet();

let onlineFailCount  = 0;
let onlineDisabledAt = 0;

let statusEl = null;

function resolveCssHref() {
  const fromCurrentScript = document.currentScript?.src;
  if (fromCurrentScript) {
    return fromCurrentScript.replace(/\/js\/danbooru_autocomplete\.js(?:\?.*)?$/, "/css/danbooru_autocomplete.css");
  }

  const script = Array.from(document.querySelectorAll("script[src]")).find(el =>
    /\/js\/danbooru_autocomplete\.js(?:\?.*)?$/.test(el.src)
  );
  if (script?.src) {
    return script.src.replace(/\/js\/danbooru_autocomplete\.js(?:\?.*)?$/, "/css/danbooru_autocomplete.css");
  }

  return "/extensions/comfyui-danbooru-autocomplete/css/danbooru_autocomplete.css";
}

(function injectStyle() {
  if (document.getElementById("dac-style")) return;
  const link = document.createElement("link");
  link.id = "dac-style";
  link.rel = "stylesheet";
  link.href = resolveCssHref();
  document.head.appendChild(link);
})();

function showStatus(text, type, durationMs = 2500) {
  if (!statusEl) {
    statusEl = document.createElement("div");
    statusEl.id = "dac-status";
    document.body.appendChild(statusEl);
  }
  statusEl.textContent = text;
  statusEl.className = `show ${type}`;
  clearTimeout(statusEl._timer);
  statusEl._timer = setTimeout(() => statusEl.classList.remove("show"), durationMs);
}

function getDropdown() {
  if (!dropdownEl) {
    dropdownEl = document.createElement("div");
    dropdownEl.id = "dac-dropdown";
    dropdownEl.addEventListener("mousedown", e => e.preventDefault());
    document.body.appendChild(dropdownEl);
  }
  return dropdownEl;
}

function showDropdown(items, query, source) {
  const dd = getDropdown();
  results = items;
  selectedIdx = -1;
  dd.innerHTML = "";

  if (!items.length || !activeTextarea) { hideDropdown(); return; }

  const srcLabel = source === "online"
    ? `<span class="dac-header-src online">● Danbooru Live</span>`
    : `<span class="dac-header-src local">● Local</span>`;
  const hdr = document.createElement("div");
  hdr.className = "dac-header";
  hdr.innerHTML = `<span>Danbooru  ·  ${items.length} tags</span>${srcLabel}`;
  dd.appendChild(hdr);

  const lq = query.toLowerCase();
  items.forEach((item, i) => {
    const el = document.createElement("div");
    el.className = "dac-item";
    el.dataset.i = i;

    const color = CATEGORY_COLORS[item.category] ?? "#888";
    const cat   = CATEGORY_NAMES[item.category]  ?? "other";

    const t  = item.tag;
    const li = t.toLowerCase().indexOf(lq);
    const hi = li >= 0
      ? `${esc(t.slice(0, li))}<em>${esc(t.slice(li, li + query.length))}</em>${esc(t.slice(li + query.length))}`
      : esc(t);

    el.innerHTML = `
      <span class="dac-tag">${hi}</span>
      <span class="dac-cnt">${fmtCount(item.count)}</span>
      <span class="dac-cat" style="background:${color}1a;color:${color};border:1px solid ${color}55">${cat}</span>`;

    el.addEventListener("click", () => insertTag(item.tag));
    dd.appendChild(el);
  });

  positionDropdown(dd);
  dd.style.display = "block";
}

function positionDropdown(dd) {
  if (!activeTextarea) return;
  const r   = activeTextarea.getBoundingClientRect();
  const ddH = Math.min(320, results.length * 33 + 36);
  const below = window.innerHeight - r.bottom;
  const top   = below >= ddH || below >= r.top ? r.bottom + 3 : r.top - ddH - 3;
  const left  = Math.max(4, Math.min(r.left, window.innerWidth - 450));
  dd.style.top  = `${top}px`;
  dd.style.left = `${left}px`;
}

function hideDropdown() {
  if (dropdownEl) dropdownEl.style.display = "none";
  selectedIdx = -1;
  results = [];
}

function moveSelection(delta) {
  const dd = dropdownEl;
  if (!dd || dd.style.display === "none") return false;
  const items = dd.querySelectorAll(".dac-item");
  if (!items.length) return false;
  items[selectedIdx]?.classList.remove("dac-sel");
  selectedIdx = Math.max(-1, Math.min(items.length - 1, selectedIdx + delta));
  if (selectedIdx >= 0) {
    items[selectedIdx].classList.add("dac-sel");
    items[selectedIdx].scrollIntoView({ block: "nearest" });
  }
  return true;
}

function insertTag(tag) {
  const ta = activeTextarea;
  if (!ta) return;

  const val    = ta.value;
  const cursor = ta.selectionStart;

  const before   = val.slice(0, cursor);
  const sepIdx   = Math.max(before.lastIndexOf(","), before.lastIndexOf("\n"));
  const tokStart = sepIdx + 1;

  const after   = val.slice(cursor);
  const nextSep = after.search(/[,\n]/);
  const tokEnd  = nextSep === -1 ? val.length : cursor + nextSep;

  const leftRaw  = val.slice(0, tokStart);
  const rightRaw = val.slice(tokEnd);

  let prefix;
  if (!leftRaw.trimEnd()) {
    prefix = "";
  } else if (leftRaw[leftRaw.length - 1] === "\n") {
    prefix = leftRaw;
  } else {
    prefix = leftRaw.replace(/[,\s]+$/, "") + ", ";
  }

  let suffix;
  if (!rightRaw) {
    suffix = ", ";
  } else if (rightRaw[0] === "\n") {
    suffix = ", " + rightRaw;
  } else if (rightRaw[0] === ",") {
    suffix = rightRaw;
  } else {
    suffix = ", " + rightRaw.trimStart();
  }

  const newVal    = prefix + tag + suffix;
  const newCursor = prefix.length + tag.length + 2;

  ta.value = newVal;
  ta.setSelectionRange(newCursor, newCursor);

  ta.dispatchEvent(new Event("input",  { bubbles: true }));
  ta.dispatchEvent(new Event("change", { bubbles: true }));

  hideDropdown();
  ta.focus();
}

function isOnlineAvailable() {
  if (onlineFailCount < ONLINE_FAIL_THRESHOLD) return true;
  return Date.now() - onlineDisabledAt > ONLINE_RETRY_MS;
}

async function fetchFromDanbooru(query, signal) {
  const r = await fetch(
    `${ONLINE_API}?q=${encodeURIComponent(query)}&limit=20`,
    { signal }
  );
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const data = await r.json();
  return Array.isArray(data) ? data : [];
}

async function fetchFromLocal(query, signal) {
  const r = await fetch(
    `${LOCAL_API}?q=${encodeURIComponent(query)}&limit=20`,
    { signal }
  );
  if (!r.ok) return [];
  const data = await r.json();
  return Array.isArray(data) ? data : [];
}

async function fetchTags(query) {
  if (abortCtrl) abortCtrl.abort();
  abortCtrl = new AbortController();
  const signal = abortCtrl.signal;

  if (isOnlineAvailable()) {
    try {
      const items = await fetchFromDanbooru(query, signal);
      onlineFailCount = 0;
      onlineDisabledAt = 0;
      return { items, source: "online" };
    } catch (e) {
      if (e.name === "AbortError") throw e;
      onlineFailCount++;
      if (onlineFailCount >= ONLINE_FAIL_THRESHOLD) {
        onlineDisabledAt = Date.now();
        console.warn(
          `[DanbooruAC] 在线 API 连续失败 ${onlineFailCount} 次，` +
          `暂停 ${ONLINE_RETRY_MS / 1000}s 后重试。错误：${e.message}`
        );
        showStatus("⚠ Danbooru offline · using local", "local", 4000);
      }
    }
  }

  try {
    const items = await fetchFromLocal(query, signal);
    return { items, source: "local" };
  } catch (e) {
    if (e.name !== "AbortError") console.warn("[DanbooruAC] local:", e.message);
    return { items: [], source: "local" };
  }
}

function getCurrentToken(ta) {
  const before = ta.value.slice(0, ta.selectionStart);
  const sep    = Math.max(before.lastIndexOf(","), before.lastIndexOf("\n"));
  return before.slice(sep + 1).trimStart();
}

function onTextareaInput(ta) {
  activeTextarea = ta;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    if (activeTextarea !== ta) return;
    const token = getCurrentToken(ta);
    if (token.length < 2) { hideDropdown(); return; }

    const dd = getDropdown();
    const existingHdr = dd.querySelector(".dac-header");
    if (dd.style.display === "block" && existingHdr) {
      existingHdr.querySelector(".dac-header-src")?.replaceWith(
        Object.assign(document.createElement("span"), {
          className: "dac-header-src loading",
          textContent: "○ loading…"
        })
      );
    }

    try {
      const { items, source } = await fetchTags(token);
      if (activeTextarea !== ta) return;
      showDropdown(items, token, source);
      if (source === "online" && items.length > 0) {
        showStatus("● Danbooru Live", "online");
      }
    } catch (e) {
      if (e.name !== "AbortError") console.warn("[DanbooruAC]", e);
    }
  }, 200);
}

function onTextareaKeydown(e) {
  const dd = dropdownEl;
  if (!dd || dd.style.display === "none") return;

  switch (e.key) {
    case "ArrowDown": e.preventDefault(); moveSelection(+1); break;
    case "ArrowUp":   e.preventDefault(); moveSelection(-1); break;
    case "Enter":
    case "Tab":
      if (selectedIdx >= 0 && results[selectedIdx]) {
        e.preventDefault();
        e.stopPropagation();
        insertTag(results[selectedIdx].tag);
      } else if (e.key === "Tab") {
        hideDropdown();
      }
      break;
    case "Escape":
      e.preventDefault();
      hideDropdown();
      break;
  }
}

function looksLikePromptTextarea(ta) {
  if (ta.classList.contains("comfy-multiline-input")) return true;
  let el = ta.parentElement;
  let depth = 0;
  while (el && depth < 8) {
    if (el.tagName === "CANVAS") return true;
    if (/lgraph|litecanvas|comfy/i.test(el.className || "")) return true;
    el = el.parentElement;
    depth++;
  }
  const st = window.getComputedStyle(ta);
  if (st.position === "fixed" || st.position === "absolute") return true;
  const r = ta.getBoundingClientRect();
  return r.width > 40 && r.height > 30;
}

function bindTextarea(ta) {
  if (patchedSet.has(ta)) return;
  if (!looksLikePromptTextarea(ta)) return;
  patchedSet.add(ta);

  ta.addEventListener("input",   () => onTextareaInput(ta));
  ta.addEventListener("keydown", onTextareaKeydown, true);
  ta.addEventListener("blur",    () => setTimeout(hideDropdown, 180));
  ta.addEventListener("focus",   () => { activeTextarea = ta; });
}

function scanAndBind(root) {
  (root || document).querySelectorAll("textarea").forEach(bindTextarea);
}

const observer = new MutationObserver(mutations => {
  for (const m of mutations) {
    for (const node of m.addedNodes) {
      if (node.nodeType !== 1) continue;
      if (node.tagName === "TEXTAREA") bindTextarea(node);
      else node.querySelectorAll?.("textarea").forEach(bindTextarea);
    }
  }
});

function init() {
  scanAndBind(document);
  observer.observe(document.body, { childList: true, subtree: true });
  document.addEventListener("click", () => setTimeout(() => scanAndBind(document), 120), true);
  document.addEventListener("focusin", e => {
    if (e.target.tagName === "TEXTAREA") bindTextarea(e.target);
  });
  console.log("[DanbooruAutocomplete] ✓ 已加载（在线 Danbooru API + 本地降级）");
}

function fmtCount(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(n || 0);
}
function esc(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

if (typeof window.__comfy_extension !== "undefined" ||
    (typeof window.app !== "undefined" && window.app?.registerExtension)) {
  try {
    (window.app ?? window.__comfy_extension).registerExtension({
      name: "DanbooruAutocomplete",
      async setup() { init(); }
    });
  } catch (e) {
    if (document.readyState === "loading")
      document.addEventListener("DOMContentLoaded", init);
    else init();
  }
} else {
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
}

setTimeout(() => scanAndBind(document), 2000);