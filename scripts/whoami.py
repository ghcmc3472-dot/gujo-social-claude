"""토큰이 어느 계정 것인지, 게시 권한이 있는지만 확인한다. 아무것도 올리지 않는다."""
import json, os, urllib.parse, urllib.request, urllib.error


def get(url, tok):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tok})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        try:
            return {'error': json.loads(e.read()).get('error', {}).get('message', str(e))}
        except Exception:
            return {'error': str(e)}


out = {}
ig = os.environ.get('IG_TOKEN', '').strip()
if ig:
    if ig.startswith('EAA'):
        FBG = 'https://graph.facebook.com/v21.0'
        r = {'type': 'facebook-login'}
        pages = get(f'{FBG}/me/accounts?fields=name,instagram_business_account{{username}}', ig)
        r['pages'] = pages
        dbg = get(f'{FBG}/debug_token?input_token={ig}', ig).get('data', {})
        r['expires_at'] = dbg.get('expires_at'); r['scopes'] = dbg.get('scopes')
        uid = next((p['instagram_business_account']['id'] for p in pages.get('data', []) if p.get('instagram_business_account')), None)
        if uid:
            r['publish_limit'] = get(f'{FBG}/{uid}/content_publishing_limit?fields=quota_usage,config', ig)
            def songs(q=None):
                u = f'{FBG}/ig_audio?audio_type=music&user_id={uid}' + (f'&search_query={urllib.parse.quote(q)}' if q else '')
                d = get(u, ig)
                return d if 'error' in d else [f"{x.get('title')} — {x.get('display_artist')} ({int(x.get('duration_in_ms') or 0)//1000}s)" for x in d.get('data', [])[:10]]
            r['music_trending'] = songs()
            r['music_piano'] = songs('piano')
        out['instagram'] = r
    else:
        me = get('https://graph.instagram.com/v21.0/me?fields=user_id,username,account_type', ig)
        r = {'type': 'instagram-login', 'me': me}
        if 'user_id' in me:
            r['publish_limit'] = get(f"https://graph.instagram.com/v21.0/{me['user_id']}/content_publishing_limit?fields=quota_usage,config", ig)
        out['instagram'] = r
th = os.environ.get('THREADS_TOKEN', '').strip()
if th:
    out['threads'] = get('https://graph.threads.net/v1.0/me?fields=id,username', th)
print(json.dumps(out, ensure_ascii=False, indent=1))
os.makedirs('state', exist_ok=True)
json.dump(out, open('state/whoami.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 클로드 구독 토큰 확인 (짧은 호출 1회)
import shutil, subprocess
if os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') and shutil.which('claude'):
    p = subprocess.run(['claude', '-p', '"확인"이라고만 답하세요', '--model', 'haiku'], capture_output=True, text=True, timeout=120)
    out['claude'] = (p.stdout.strip() or p.stderr.strip())[:200]
    json.dump(out, open('state/whoami.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('claude:', out['claude'])
