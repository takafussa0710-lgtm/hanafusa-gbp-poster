#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拠点ID取得ヘルパー（一度だけ実行）
各GBPの「accounts/{id}/locations/{id}」を一覧表示する。
出力された4拠点のリソース名を、GitHub Secrets（LOC_SENRICHUO 等）に登録する。

環境変数: GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN
"""
import os, json, urllib.request, urllib.parse

TOKEN_URL = "https://oauth2.googleapis.com/token"
ACCT_API = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
INFO_API = "https://mybusinessbusinessinformation.googleapis.com/v1"

def token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["GBP_CLIENT_ID"],
        "client_secret": os.environ["GBP_CLIENT_SECRET"],
        "refresh_token": os.environ["GBP_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data)) as r:
        return json.load(r)["access_token"]

def get(url, tk):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {tk}")
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def main():
    tk = token()
    accts = get(ACCT_API, tk).get("accounts", [])
    for a in accts:
        acct_name = a["name"]  # "accounts/123..."
        print(f"\n=== {acct_name}  ({a.get('accountName','')}) ===")
        url = f"{INFO_API}/{acct_name}/locations?readMask=name,title&pageSize=100"
        locs = get(url, tk).get("locations", [])
        for L in locs:
            # L['name'] は "locations/567..." 形式。v4投稿APIは accounts/{id}/locations/{id} が必要
            loc_id = L["name"].split("/")[-1]
            resource = f"{acct_name}/locations/{loc_id}"
            print(f"  {L.get('title','(no title)')}")
            print(f"    -> {resource}")

if __name__ == "__main__":
    main()
