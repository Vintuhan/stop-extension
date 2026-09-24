#!/usr/bin/env python3
"""Собирает blocklist.json.

Источники:
  1. tools/seed_domains.txt : ваши домены вручную;
  2. tools/keywords.txt     : ключевые слова для «зеркал»;
  3. tools/allowlist.txt    : сайты, которые нельзя блокировать никогда;
  4. tools/llm_results.json : вердикты нейросети (см. classify_domains.py);
  5. открытые списки (обновляются автоматически, каждый день или чаще):
     - The Block List Project (Unlicense, свободное использование);
     - HaGeZi Gambling (лицензия GPL-3.0, см. переключатель USE_HAGEZI ниже).

Запуск:  python3 tools/update_blocklist.py
Только стандартная библиотека Python.
"""
import collections
import datetime
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
OUT = ROOT / "blocklist.json"

# HaGeZi распространяется под GPL-3.0. Если вы публикуете свой blocklist.json
# вместе с доменами из него, публикуйте репозиторий тоже под GPL-3.0.
# Не хотите этого: поставьте False, останется список Block List Project.
USE_HAGEZI = True

SOURCES = [("blocklistproject",
            "https://raw.githubusercontent.com/blocklistproject/Lists/master/gambling.txt")]
if USE_HAGEZI:
    SOURCES.append(("hagezi",
                    "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/gambling-onlydomains.txt"))

# Сколько доменов брать из больших открытых списков (в них сотни тысяч записей).
MAX_PUBLIC = 15000
# Минимальная уверенность нейросети, чтобы домен попал в список сам.
MIN_CONFIDENCE = 0.9

DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")


def read_lines(name):
    path = TOOLS / name
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            out.append(line)
    return out


def fetch_source(name, url):
    print(f"Скачиваю {name}...")
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            text = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  не удалось: {e}")
        return set()
    found = set()
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        d = line.split()[-1].lower()
        if DOMAIN_RE.match(d):
            found.add(d)
    print(f"  доменов: {len(found)}")
    return found


def fetch_all():
    """Возвращает {домен: сколько списков его содержат}."""
    counts = collections.Counter()
    for name, url in SOURCES:
        for d in fetch_source(name, url):
            counts[d] += 1
    return counts


def llm_approved():
    path = TOOLS / "llm_results.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return sorted(
        d for d, v in data.items()
        if v.get("gambling") and float(v.get("confidence", 0)) >= MIN_CONFIDENCE
        and DOMAIN_RE.match(d)
    )


def main():
    seed = [d for d in read_lines("seed_domains.txt") if DOMAIN_RE.match(d)]
    keywords = read_lines("keywords.txt")
    allow = [d for d in read_lines("allowlist.txt") if DOMAIN_RE.match(d)]
    ai = llm_approved()

    counts = fetch_all()

    def blocked_by_us(d):
        return d in own or any(k in d for k in keywords)

    own = set(seed) | set(ai)
    # Домены, которые уже закрыты ключевыми словами, в список не кладём.
    # Остальные ранжируем: сначала те, что есть в нескольких списках, потом короткие
    # (настоящие бренды обычно короче автоматически созданных зеркал).
    candidates = [d for d in counts if not blocked_by_us(d)]
    candidates.sort(key=lambda d: (-counts[d], len(d), d))
    picked = candidates[:MAX_PUBLIC]

    domains = sorted(own) + picked
    allow_set = set(allow)
    domains = [d for d in domains if d not in allow_set]

    data = {
        "updated": datetime.date.today().isoformat(),
        "keywords": keywords,
        "allow": sorted(allow_set),
        "domains": domains,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"Готово: {len(domains)} доменов, {len(keywords)} ключевых слов, "
          f"{len(allow_set)} исключений (из них от нейросети: {len(ai)}) -> {OUT.name}")


if __name__ == "__main__":
    main()
