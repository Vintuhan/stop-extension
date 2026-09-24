"use strict";

// Куда расширение ходит за свежим списком. Пока пусто: работает встроенный blocklist.json.
// Позже сюда можно вставить ссылку на свой файл, например:
// "https://raw.githubusercontent.com/ВАШ_НИК/ВАШ_РЕПОЗИТОРИЙ/main/blocklist.json"
const REMOTE_URL = "";

const REFRESH_MINUTES = 360; // как часто обновлять список (раз в 6 часов)
const CHUNK = 1000;          // доменов в одном правиле
const ALARM = "stop-refresh";

const DOMAIN_RE = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$/;
const KEYWORD_RE = /^[a-z0-9.-]{3,40}$/;

async function loadLists() {
  const lists = [];
  const bundled = await fetch(chrome.runtime.getURL("blocklist.json"));
  lists.push(await bundled.json());

  let remote = null;
  if (REMOTE_URL) {
    try {
      const r = await fetch(REMOTE_URL, { cache: "no-store" });
      if (r.ok) {
        remote = await r.json();
        await chrome.storage.local.set({ remote });
      }
    } catch (e) {
      // нет сети — используем то, что скачали в прошлый раз
    }
  }
  if (!remote) {
    remote = (await chrome.storage.local.get("remote")).remote || null;
  }
  if (remote) lists.push(remote);
  return lists;
}

function merge(lists) {
  const domains = new Set();
  const keywords = new Set();
  const allow = new Set();
  for (const l of lists) {
    for (const d of l.allow || []) {
      const x = String(d).trim().toLowerCase().replace(/^www\./, "");
      if (DOMAIN_RE.test(x)) allow.add(x);
    }
    for (const d of l.domains || []) {
      const x = String(d).trim().toLowerCase().replace(/^www\./, "");
      if (DOMAIN_RE.test(x)) domains.add(x);
    }
    for (const k of l.keywords || []) {
      const x = String(k).trim().toLowerCase();
      if (KEYWORD_RE.test(x)) keywords.add(x);
    }
  }
  return { domains: [...domains], keywords: [...keywords], allow: [...allow] };
}

async function applyRules({ domains, keywords, allow }) {
  const action = { type: "redirect", redirect: { extensionPath: "/blocked.html" } };
  const rules = [];
  let id = 1;

  // Исключения (сайты помощи и всё, что заблокировалось по ошибке): приоритет выше блокировок
  for (let i = 0; i < allow.length; i += CHUNK) {
    rules.push({
      id: id++,
      priority: 2,
      action: { type: "allow" },
      condition: {
        requestDomains: allow.slice(i, i + CHUNK),
        resourceTypes: ["main_frame"],
      },
    });
  }

  // «Зеркала»: по маленькому правилу на каждое ключевое слово (1xbet и т.п.).
  // Одно общее правило на все слова не влезает в лимит браузера (2 КБ на регулярное выражение).
  for (const k of keywords.slice(0, 500)) {
    const regex = "^https?://[^/?#]*" + k.replace(/\./g, "\\.");
    if (chrome.declarativeNetRequest.isRegexSupported) {
      const check = await chrome.declarativeNetRequest.isRegexSupported({ regex });
      if (!check.isSupported) {
        console.warn("Стоп: пропущено слово", k, check.reason);
        continue;
      }
    }
    rules.push({
      id: id++,
      priority: 1,
      action,
      condition: { regexFilter: regex, resourceTypes: ["main_frame"] },
    });
  }

  // Точные домены (вместе с поддоменами), пачками по CHUNK штук
  for (let i = 0; i < domains.length; i += CHUNK) {
    rules.push({
      id: id++,
      priority: 1,
      action,
      condition: {
        requestDomains: domains.slice(i, i + CHUNK),
        resourceTypes: ["main_frame"],
      },
    });
  }

  const old = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: old.map((r) => r.id),
    addRules: rules,
  });
}

let running = null;
function refresh() {
  if (!running) {
    running = loadLists()
      .then((lists) => applyRules(merge(lists)))
      .catch((e) => console.error("Стоп: не удалось обновить правила", e))
      .finally(() => { running = null; });
  }
  return running;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM, { periodInMinutes: REFRESH_MINUTES });
  refresh();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(ALARM, { periodInMinutes: REFRESH_MINUTES });
  refresh();
});

chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === ALARM) refresh();
});
