#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【一回限り】江坂の公開済み投稿のうち「皮膚科専門医」表記のものを削除し、
修正版（ベテランの皮膚科医）で再投稿する。＋7/9未投稿のシルファームも投稿。
GitHub Actions（workflow_dispatch）から Secrets を使って実行する想定。
"""
import os, json, urllib.request, urllib.error
import post_to_gbp as g

def main():
    LOC = os.environ["LOC_ESAKA"]
    images_base = os.environ.get("IMAGES_BASE_URL", "")
    token = g.get_access_token()

    # 1) 既存の江坂ローカル投稿を取得
    def get(url):
        req = urllib.request.Request(url); req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    posts = get(f"{g.API_BASE}/{LOC}/localPosts").get("localPosts", [])
    print(f"江坂の公開投稿数: {len(posts)}")

    # 2) 「皮膚科専門医」を含む投稿を削除
    deleted = 0
    for p in posts:
        if "皮膚科専門医" in p.get("summary", ""):
            name = p["name"]  # accounts/.../localPosts/...
            req = urllib.request.Request(f"{g.API_BASE}/{name}", method="DELETE")
            req.add_header("Authorization", "Bearer " + token)
            try:
                urllib.request.urlopen(req)
                deleted += 1
                print(f"[削除] {p['summary'][:26]}…")
            except Exception as e:
                print(f"[削除失敗] {e}: {p['summary'][:26]}")
    print(f"削除件数: {deleted}")

    # 3) 修正版を再投稿（content.json の江坂・修正済み文面）
    content = json.load(open("posts/content.json", encoding="utf-8"))["LOC_ESAKA"]
    for key in ["zenshin_datsumo", "miradry", "sylfirm"]:
        try:
            st = g.create_post(token, LOC, content[key], images_base)
            print(f"[再投稿] {key}: {st}")
        except Exception as e:
            print(f"[再投稿失敗] {key}: {e}")

if __name__ == "__main__":
    main()
