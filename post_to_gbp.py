#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBP 自動投稿スクリプト（GitHub Actions から毎日実行）
- OAuth リフレッシュトークンでアクセストークンを取得
- posts/<拠点>.json から「今日の投稿」を選んで GBP に投稿（localPosts.create）
- 同一文の連投を避けるため、日付で投稿をローテーション

必要な環境変数（GitHub Secrets）:
  GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN
  LOC_SENRICHUO, LOC_ESAKA, LOC_MINOH, LOC_LAB
    例: "accounts/1234567890/locations/9876543210"
"""
import os, json, sys, datetime
import urllib.request, urllib.parse

TOKEN_URL = "https://oauth2.googleapis.com/token"
# GBP 投稿API（localPosts）は v4 エンドポイント
API_BASE = "https://mybusiness.googleapis.com/v4"

# 投稿先：環境変数名 -> posts/ のファイル名
LOCATIONS = {
    "LOC_SENRICHUO": "senrichuo",
    "LOC_ESAKA":     "esaka",
    "LOC_MINOH":     "minoh",
    "LOC_LAB":       "lab",
}

# 休診日ルール（曜日: Mon=0 .. Sun=6）。該当拠点はその曜日は配信しない。
# ・日曜(6)は全院休診 → 全拠点配信しない
# ・江坂・ラボは水曜(2)も休み
# （日替わり・キャンペーン共通で自動適用）
JST = datetime.timezone(datetime.timedelta(hours=9))
CLOSED_WEEKDAYS = {
    "LOC_SENRICHUO": {6},
    "LOC_ESAKA":     {2, 6},
    "LOC_MINOH":     {6},
    "LOC_LAB":       {2, 6},
}

def is_closed_today(env_name):
    wd = datetime.datetime.now(JST).weekday()
    return wd in CLOSED_WEEKDAYS.get(env_name, set())

def get_access_token():
    data = urllib.parse.urlencode({
        "client_id":     os.environ["GBP_CLIENT_ID"],
        "client_secret": os.environ["GBP_CLIENT_SECRET"],
        "refresh_token": os.environ["GBP_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data)
    with urllib.request.urlopen(req) as r:
        return json.load(r)["access_token"]

def pick_todays_post(posts):
    """日付（年内通算日）でローテーションし、同じ投稿の連投を避ける"""
    doy = datetime.date.today().timetuple().tm_yday
    return posts[doy % len(posts)]

def create_post(token, location_resource, post, images_base=""):
    url = f"{API_BASE}/{location_resource}/localPosts"
    body = {
        "languageCode": "ja",
        "summary": post["summary"],
        "topicType": post.get("topicType", "STANDARD"),
    }
    cta = post.get("callToAction")
    if cta:
        body["callToAction"] = cta  # 例: {"actionType":"LEARN_MORE","url":"https://..."}
    # 画像（任意）: "image"=単一、"images"=複数（日替わりローテ）。フルURL or ファイル名（ファイル名は IMAGES_BASE_URL を前置）。
    img = post.get("image")
    imgs = post.get("images")
    if imgs:
        img = imgs[datetime.date.today().timetuple().tm_yday % len(imgs)]
    if img:
        img_url = img if img.startswith("http") else (images_base.rstrip("/") + "/" + img if images_base else "")
        if img_url:
            body["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": img_url}]
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return r.status

def main():
    token = get_access_token()
    images_base = os.environ.get("IMAGES_BASE_URL", "")  # 例: GitHubの raw URL https://raw.githubusercontent.com/<user>/<repo>/main/images
    # 本日だけ特定拠点をスキップ（例: キャンペーン投稿と重複させたくない日）。環境変数 SKIP_LOCATIONS="LOC_SENRICHUO,LOC_MINOH"
    skip = {x.strip() for x in os.environ.get("SKIP_LOCATIONS", "").split(",") if x.strip()}
    failures = 0
    for env_name, file_key in LOCATIONS.items():
        if env_name in skip:
            print(f"[skip] {env_name} は本日スキップ指定")
            continue
        if is_closed_today(env_name):
            print(f"[skip] {env_name} は本日休診日のため配信しない")
            continue
        loc = os.environ.get(env_name)
        if not loc:
            print(f"[skip] {env_name} 未設定")
            continue
        path = os.path.join("posts", f"{file_key}.json")
        if not os.path.exists(path):
            print(f"[skip] {path} なし")
            continue
        with open(path, encoding="utf-8") as f:
            posts = json.load(f)
        if not posts:
            print(f"[skip] {path} 空")
            continue
        post = pick_todays_post(posts)
        try:
            status = create_post(token, loc, post, images_base)
            print(f"[ok] {file_key}: {status} 「{post['summary'][:24]}…」")
        except Exception as e:
            failures += 1
            print(f"[ERROR] {file_key}: {e}")
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
