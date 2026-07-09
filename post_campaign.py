#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
キャンペーン投稿スクリプト（特定テーマを指定拠点へ一斉投稿）
使い方: python post_campaign.py posts/campaign_xxx.json
各エントリは {"loc": "LOC_XXX", "summary": ..., "callToAction": ..., 任意で image/images}。
"loc" は GitHub Secrets のロケーション環境変数名（LOC_SENRICHUO 等）。
"""
import os, json, sys
import post_to_gbp as g

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'posts/campaign.json'
    images_base = os.environ.get('IMAGES_BASE_URL', '')
    with open(path, encoding='utf-8') as f:
        entries = json.load(f)
    token = g.get_access_token()
    fail = 0
    for e in entries:
        if g.is_closed_today(e['loc']):
            print(f"[skip] {e['loc']} は本日休診日のため配信しない")
            continue
        loc = os.environ.get(e['loc'])
        if not loc:
            print(f"[skip] {e['loc']} 未設定"); continue
        try:
            st = g.create_post(token, loc, e, images_base)
            print(f"[ok] {e['loc']}: {st} 「{e['summary'][:24]}…」")
        except Exception as ex:
            fail += 1
            print(f"[ERROR] {e['loc']}: {ex}")
    sys.exit(1 if fail else 0)

if __name__ == '__main__':
    main()
