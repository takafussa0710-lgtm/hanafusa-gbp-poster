#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ロケーションID取得ツール（500エラーを自動リトライで突破）
使い方:
  1) OAuth Playground の「Refresh token」欄の値をコピー（Cmd+C）しておく
  2) このスクリプトを実行:  python3 fetch_locations.py
  - クライアントID/シークレットは ~/Downloads/client_secret_*.json から自動読込
  - リフレッシュトークンはクリップボード(pbpaste)から取得（画面には出さない）
  - locations.list の 500 は最大60回・指数バックオフでリトライ
  出力: accounts/… と locations/… の対応表（= 自動投稿の LOC_ 値）
"""
import json, glob, subprocess, sys, time
import urllib.request, urllib.parse, urllib.error

def load_client():
    files = sorted(glob.glob('/Users/takafussa/Downloads/client_secret_*.json'))
    if not files:
        print('ERROR: ~/Downloads に client_secret_*.json が見つかりません'); sys.exit(1)
    d = json.load(open(files[-1]))
    w = d.get('web') or d.get('installed')
    return w['client_id'], w['client_secret']

def get_refresh_from_clipboard():
    try:
        v = subprocess.check_output(['pbpaste']).decode().strip()
    except Exception:
        v = ''
    if not v.startswith('1//'):
        print('ERROR: クリップボードにリフレッシュトークン（1// で始まる値）がありません。')
        print('       OAuth Playground の Refresh token 欄をクリック→Cmd+A→Cmd+C でコピーしてから再実行してください。')
        sys.exit(1)
    return v

def access_token(cid, csec, refresh):
    data = urllib.parse.urlencode({
        'client_id': cid, 'client_secret': csec,
        'refresh_token': refresh, 'grant_type': 'refresh_token',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    with urllib.request.urlopen(req) as r:
        return json.load(r)['access_token']

def api_get(url, token, tries=1):
    last = None
    for i in range(tries):
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (500, 503, 429):
                wait = min(2 ** min(i, 5), 30)
                print(f'  ...{e.code} リトライ {i+1}/{tries}（{wait}s待機）', flush=True)
                time.sleep(wait); continue
            raise
    raise last

def main():
    cid, csec = load_client()
    refresh = get_refresh_from_clipboard()
    token = access_token(cid, csec, refresh)
    print('アクセストークン取得OK。アカウント/ロケーションを取得します…\n', flush=True)

    accts = api_get('https://mybusinessaccountmanagement.googleapis.com/v1/accounts', token, tries=10).get('accounts', [])
    if not accts:
        print('アカウントが見つかりません。'); return
    for a in accts:
        aid = a['name']  # accounts/NNN
        print(f'== {aid}  ({a.get("accountName")}, {a.get("type")}) ==', flush=True)
        base = f'https://mybusinessbusinessinformation.googleapis.com/v1/{aid}/locations?readMask=name,title,storefrontAddress&pageSize=100'
        url = base
        got = []
        while True:
            try:
                r = api_get(url, token, tries=60)
            except Exception as e:
                print(f'  取得失敗: {e}'); break
            got += r.get('locations', [])
            npt = r.get('nextPageToken')
            if not npt: break
            url = base + '&pageToken=' + urllib.parse.quote(npt)
        if not got:
            print('  （ロケーションなし）')
        for l in got:
            addr = l.get('storefrontAddress', {})
            city = ''.join(addr.get('addressLines', []) or []) or addr.get('locality', '')
            # 投稿APIで使う形式: accounts/NNN/locations/MMM
            loc_res = f'{aid}/{l["name"]}'  # l["name"] = locations/MMM
            print(f'  {loc_res}  |  {l.get("title")}  |  {city}')
    print('\n完了。上の accounts/.../locations/... が LOC_ の値です。')

if __name__ == '__main__':
    main()
