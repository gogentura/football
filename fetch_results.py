# Скачивает результаты сыгранных матчей с football-data.org и сохраняет в results.json.
# Ключ берётся из переменной окружения FOOTBALL_DATA_TOKEN (её задаёт GitHub Actions).
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
        seen = {(m[0], m[1], m[2]) for m in league["matches"]}
        added = 0
        for m in js.get("matches", []):
            sc = m.get("score") or {}
            # Для матчей с дополнительным временем берём счёт основного времени (90 минут)
            ft = sc.get("regularTime") or sc.get("fullTime") or {}
            gh, ga = ft.get("home"), ft.get("away")
            if gh is None or ga is None:
                continue
            row = [m["utcDate"][:10], m["homeTeam"]["name"], m["awayTeam"]["name"], gh, ga]
            key = (row[0], row[1], row[2])
            if key in seen:
                continue
            seen.add(key)
            league["matches"].append(row)
            added += 1
        league["matches"].sort(key=lambda r: r[0])
        print(code, "новых матчей:", added, "всего:", len(league["matches"]))
        ok += 1

    if ok == 0:
        print("Ни одна лига не загрузилась, файл не изменён")
        sys.exit(1)
    data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
