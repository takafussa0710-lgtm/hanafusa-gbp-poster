"""GBP の「検索語」データ(Business Profile Performance API)を月 1 回取得する。読み取りのみ。
G9(2026-11-10): アビクリア関連語で千里中央・みのおが何回見つかったかを記録する。
出力は該当語(アビクリア・ニキビ)の件数だけ。リポジトリが公開のため、それ以外の語はログに出さない。
使い方: GBP_CLIENT_ID/SECRET/REFRESH_TOKEN と LOC_SENRICHUO / LOC_MINOH を環境変数で渡す。
  MONTHS=3 で直近 3 か月(既定 1 = 前月)。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request

from post_to_gbp import get_access_token

BASE = "https://businessprofileperformance.googleapis.com/v1"
TARGETS = {"LOC_SENRICHUO": "千里中央", "LOC_MINOH": "みのお"}
WORDS = ("アビクリア", "aviclear", "ニキビ", "にきび")


def month_range(n: int):
    today = dt.date.today().replace(day=1)
    end = today - dt.timedelta(days=1)
    start = end
    for _ in range(n - 1):
        start = (start.replace(day=1) - dt.timedelta(days=1))
    return start.replace(day=1), end


def fetch(token: str, loc_id: str, start: dt.date, end: dt.date) -> list:
    rows, page = [], ""
    while True:
        q = {"monthlyRange.startMonth.year": start.year, "monthlyRange.startMonth.month": start.month,
             "monthlyRange.endMonth.year": end.year, "monthlyRange.endMonth.month": end.month, "pageSize": 100}
        if page:
            q["pageToken"] = page
        url = f"{BASE}/locations/{loc_id}/searchkeywords/impressions/monthly?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        rows += d.get("searchKeywordsCounts", [])
        page = d.get("nextPageToken", "")
        if not page:
            return rows


def main() -> None:
    n = int(os.environ.get("MONTHS", "1"))
    start, end = month_range(n)
    token = get_access_token()
    print(f"期間: {start:%Y-%m} 〜 {end:%Y-%m}")
    for env, name in TARGETS.items():
        res = os.environ.get(env, "")
        if not res:
            print(f"{name}: {env} が未設定"); continue
        loc_id = res.rstrip("/").split("/")[-1]
        rows = fetch(token, loc_id, start, end)
        hits = [r for r in rows if any(w in r.get("searchKeyword", "").lower() for w in WORDS)]
        print(f"\n## {name}(検索語 全{len(rows)}語中 該当{len(hits)}語)")
        for r in sorted(hits, key=lambda r: -int(r.get("insightsValue", {}).get("value", 0) or 0)):
            v = r.get("insightsValue", {})
            shown = v.get("value") or f"{v.get('threshold')}未満"
            print(f"- {r['searchKeyword']}: {shown}")


if __name__ == "__main__":
    main()
