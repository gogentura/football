# Скачивает результаты сыгранных матчей с football-data.org и сохраняет в results.json.
# Ключ берётся из переменной окружения FOOTBALL_DATA_TOKEN (её задаёт GitHub Actions).
#
# Строка матча: [дата, хозяева, гости, голы_хозяев, голы_гостей].
# Если API пометил матч как FINISHED, но счёта ещё нет, строка сохраняется с null вместо голов.
# Такой матч не теряет своё место в истории. Когда счёт появится, строка обновится на месте.
# Известный счёт пустым значением никогда не затирается.
import json
import os
import sys
import time
import urllib.request

TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "")

# Код лиги -> название. Лишние строки можно удалить, бесплатный тариф даёт 12 турниров.
# Другие коды: DED (Нидерланды), PPL (Португалия), ELC (Чемпионшип).
LEAGUES = {
    "PL": "Англия. Премьер-лига",
    "PD": "Испания. Ла Лига",
    "BL1": "Германия. Бундеслига",
    "SA": "Италия. Серия A",
    "FL1": "Франция. Лига 1",
    "CL": "Лига чемпионов",
}

OUT = "results.json"


def get(code):
    url = "https://api.football-data.org/v4/competitions/%s/matches?status=FINISHED" % code
    req = urllib.request.Request(url, headers={"X-Auth-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick_goals(score):
    """Голы основного времени (для матчей с доп. временем и пенальти берём счёт 90 минут)."""
    sc = score or {}
    ft = sc.get("regularTime") or sc.get("fullTime") or {}
    gh, ga = ft.get("home"), ft.get("away")
    if isinstance(gh, int) and isinstance(ga, int):
        return gh, ga
    return None, None


def main():
    if not TOKEN:
        print("Не задан ключ FOOTBALL_DATA_TOKEN")
        sys.exit(1)
    try:
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.setdefault("leagues", {})

    ok = 0
    for i, (code, name) in enumerate(LEAGUES.items()):
        if i:
            time.sleep(7)  # лимит бесплатного тарифа: 10 запросов в минуту
        try:
            js = get(code)
        except Exception as e:
            print(code, "ошибка:", e)
            continue
        league = data["leagues"].setdefault(code, {"name": name, "matches": []})
        league["name"] = name
        index = {(m[0], m[1], m[2]): m for m in league["matches"]}
        added = updated = pending = 0
        for m in js.get("matches", []):
            gh, ga = pick_goals(m.get("score"))
            row = [m["utcDate"][:10], m["homeTeam"]["name"], m["awayTeam"]["name"], gh, ga]
            key = (row[0], row[1], row[2])
            if gh is None:
                pending += 1
                # Диагностика: почему у FINISHED-матча нет счёта. Смотрите эти строки в журнале запуска.
                print(code, "FINISHED без счёта:", row[1], "-", row[2], row[0],
                      "| id", m.get("id"), "| lastUpdated", m.get("lastUpdated"),
                      "| duration", (m.get("score") or {}).get("duration"),
                      "| winner", (m.get("score") or {}).get("winner"),
                      "| score", json.dumps(m.get("score"), ensure_ascii=False))
            old = index.get(key)
            if old is None:
                league["matches"].append(row)
                index[key] = row
                added += 1
            elif old[3] != gh or old[4] != ga:
                if gh is None:
                    continue  # известный счёт пустым значением не затираем
                old[3], old[4] = gh, ga
                updated += 1
        league["matches"].sort(key=lambda r: r[0])
        unknown = sum(1 for r in league["matches"] if r[3] is None)
        print(code, "новых:", added, "обновлено:", updated, "без счёта сейчас:", unknown,
              "всего:", len(league["matches"]))
        ok += 1

    if ok == 0:
        print("Ни одна лига не загрузилась, файл не изменён")
        sys.exit(1)
    data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
