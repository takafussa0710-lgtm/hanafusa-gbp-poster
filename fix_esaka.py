#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【安全版・一覧表示のみ】江坂の公開ローカル投稿を一覧表示する。
削除も再投稿もしない（誤削除防止のため機能を撤去）。
出力: 各投稿の name（末尾ID）・作成日・要約・「皮膚科専門医」を含むかの印。
GitHub Actions（workflow_dispatch）から Secrets を使って実行する想定。
"""
import os, json, urllib.request
import post_to_gbp as g

def main():
    LOC = os.environ["LOC_ESAKA"]
    token = g.get_access_token()
    url = f"{g.API_BASE}/{LOC}/localPosts"
    items, page = [], None
    while True:
        u = url + (f"?pageToken={page}" if page else "")
        req = urllib.request.Request(u); req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
        items += data.get("localPosts", [])
        page = data.get("nextPageToken")
        if not page:
            break
    print(f"江坂の公開投稿数: {len(items)}")
    for i, p in enumerate(items):
        pid = p.get("name", "").split("/")[-1]
        flag = "★専門医含む" if "皮膚科専門医" in p.get("summary", "") else ""
        print(f"[{i:02d}] {pid} | {p.get('createTime','')[:10]} | {flag} | {p.get('summary','')[:44]}")

if __name__ == "__main__":
    main()
