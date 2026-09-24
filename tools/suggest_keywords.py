#!/usr/bin/env python3
"""Подсказывает, какие новые бренды казино стоит добавить в keywords.txt.

Смотрит, какие слова чаще всего встречаются в адресах из открытых списков
(за вычетом слов, которые у вас уже есть) и печатает топ.
ВАЖНО: решение всегда за вами. Слово должно быть уникальным названием бренда.
Обычные слова (online, bonus, slots, royal...) добавлять нельзя, они заденут нормальные сайты.

Запуск:  python3 tools/suggest_keywords.py
"""
import collections
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import update_blocklist as ub  # noqa: E402

TOP = 60


def main():
    keywords = ub.read_lines("keywords.txt")
    counts = ub.fetch_all()
    tokens = collections.Counter()
    for d, n in counts.items():
        if n < len(ub.SOURCES) or any(k in d for k in keywords):
            continue  # берём только то, что есть во всех списках и ещё не закрыто
        parts = d.split(".")
        label = parts[-2] if len(parts) >= 2 else d
        for t in set(re.split(r"[-_]", label)):
            if len(t) >= 5 and t.isalpha():
                tokens[t] += 1
    print("\nСлово : сколько адресов. Выберите названия брендов (не общие слова):\n")
    for t, c in tokens.most_common(TOP):
        print(f"{t:20s} {c}")


if __name__ == "__main__":
    main()
