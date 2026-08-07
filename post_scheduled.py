#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曜日固定・週替わりスケジュール投稿エンジン
- posts/schedule.json … 各拠点の週×曜日のテーマ表（3週ローテ=クリニック／1週=ラボ）
- posts/content.json  … テーマごとの投稿内容（台帳）。summary/callToAction/任意で image or images
- 基準日(anchor)からの経過週で週インデックスを決定（W3→W1ループ）
- セルが null（"-"）＝その日は投稿なし（水:江坂/ラボ、日:全院 は表側で null）
- コンテンツ未登録のテーマはスキップ（移行期の穴埋め用）

環境変数:
  GBP_CLIENT_ID / GBP_CLIENT_SECRET / GBP_REFRESH_TOKEN / LOC_* / IMAGES_BASE_URL
  DRY_RUN=1   … 実際に投稿せず、投稿予定を表示
  RUN_DATE=YYYY-MM-DD … テスト用に日付を上書き

posts/closures.json … 期間限定の臨時休業（夏季休暇など）。該当拠点・期間は日替わり投稿をスキップ。
  例: [{"note": "夏季休暇2026", "start": "2026-08-09", "end": "2026-08-16", "locs": ["LOC_SENRICHUO"]}]
"""
import os, json, sys, datetime
import post_to_gbp as g

WD = ["月", "火", "水", "木", "金", "土", "日"]

def load_closures():
    path = "posts/closures.json"
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def closure_note(env_name, today, closures):
    for c in closures:
        if env_name in c.get("locs", []) and datetime.date.fromisoformat(c["start"]) <= today <= datetime.date.fromisoformat(c["end"]):
            return c.get("note", "臨時休業")
    return None

def main():
    dry = os.environ.get("DRY_RUN") == "1"
    sched = json.load(open("posts/schedule.json", encoding="utf-8"))
    content = json.load(open("posts/content.json", encoding="utf-8"))
    closures = load_closures()
    anchor = datetime.date.fromisoformat(sched["anchor"])
    run_date = os.environ.get("RUN_DATE")
    today = datetime.date.fromisoformat(run_date) if run_date else datetime.datetime.now(g.JST).date()

    delta = (today - anchor).days
    weekday = today.weekday()  # Mon=0 .. Sun=6
    print(f"# {today}（{WD[weekday]}曜） anchor={anchor} 経過{delta}日")
    if delta < 0:
        print("スケジュール開始前のため何もしません")
        return
    weeks_since = delta // 7

    token = None if dry else g.get_access_token()
    images_base = os.environ.get("IMAGES_BASE_URL", "")
    failures = 0

    for env_name, cfg in sched["clinics"].items():
        weeks = cfg["weeks"]
        widx = weeks_since % weeks
        topic = cfg["grid"][widx][weekday]
        tag = f"{env_name} W{widx+1}/{WD[weekday]}"
        note = closure_note(env_name, today, closures)
        if note:
            print(f"[休業/{note}] {tag}")
            continue
        if not topic:
            print(f"[休/なし] {tag}")
            continue
        post = content.get(env_name, {}).get(topic)
        if not post:
            print(f"[未登録] {tag} topic={topic} … コンテンツ台帳に未登録のためスキップ")
            continue
        loc = os.environ.get(env_name)
        if not loc:
            print(f"[skip] {env_name} のロケーション環境変数が未設定")
            continue
        url = (post.get("callToAction") or {}).get("url", "")
        if dry:
            img = post.get("images") or post.get("image") or "-"
            print(f"[DRY] {tag} {topic}: 「{post['summary'][:26]}…」 img={img} link={url}")
            continue
        try:
            st = g.create_post(token, loc, post, images_base)
            print(f"[ok] {tag} {topic}: {st} 「{post['summary'][:20]}…」")
        except Exception as e:
            failures += 1
            print(f"[ERROR] {tag} {topic}: {e}")

    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
