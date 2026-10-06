# GUJO Claude 계정 · 예약 게시

인스타그램과 스레드에 `posts/schedule.json`의 게시물을 정해진 시각에 자동으로 올립니다.
**`approved`가 `true`인 것만 올라갑니다.** 처음에는 모두 `false`입니다.

## 처음 한 번 설정 (10분)

1. **저장소 만들기**
   GitHub에서 New repository → 이름 `gujo-social-claude` → **Public** → Create.
   (이미지를 인스타·스레드가 가져가려면 공개 주소가 필요해서 Public이어야 합니다. 토큰은 Secrets에 들어가 공개되지 않습니다.)
2. **파일 올리기**
   이 폴더 전체를 올립니다. 웹에서는 "uploading an existing file"로 끌어다 놓으면 됩니다.
   `.github` 폴더가 숨김이라 빠지기 쉽습니다. 꼭 같이 올리세요.
3. **토큰 넣기**
   저장소 Settings → Secrets and variables → Actions → New repository secret
   - `IG_TOKEN` : 인스타그램 토큰
   - `THREADS_TOKEN` : 스레드 토큰
4. **시험**
   Actions 탭 → "예약 게시" → Run workflow → dry_run에 `true` → 실행.
   로그에 "게시: …" 목록이 보이면 연결 끝입니다(승인 전이면 목록이 비어 있는 게 정상).

## 자동 답글 (구조 AI) 켜기

내 스레드 글에 달린 새 댓글을 30분마다 읽고, Claude Code(대표님 구독)로 답을 써서 답글로 답니다. 답글 끝에 "— 구조 AI"가 붙습니다. 남의 글에는 달지 않습니다.

1. **구독 토큰 만들기:** 대표님 PC 터미널에서 `claude setup-token` → 나온 토큰을 Secrets에 `CLAUDE_CODE_OAUTH_TOKEN`으로 저장.
2. **스레드 토큰 권한:** 댓글을 읽고 답하려면 스레드 토큰에 `threads_read_replies`, `threads_manage_replies` 권한이 있어야 합니다. 없으면 토큰을 다시 받을 때 이 둘을 체크하세요.
3. **켜기:** Settings → Secrets and variables → Actions → **Variables** 탭 → `AUTO_REPLY` = `on`. 끌 때는 `off`.
4. **모델(선택):** Variables에 `REPLY_MODEL` = `opus` / `sonnet` / `haiku`. 없으면 opus.
5. **시험:** Actions → "자동 답글" → Run workflow → dry_run `true`. 로그에 댓글과 쓸 답이 보이고, 실제로는 안 올라갑니다.

- 댓글이 여러 개면 한 번에 모아 한 번만 Claude를 부릅니다(사용량 절약).
- 한 번에 최대 15개, 하루 최대 80개.
- 스팸·욕설·광고는 답하지 않습니다(SKIP).
- 답 말투와 규칙은 `scripts/reply_persona.md`에서 바로 고칠 수 있습니다.
- 기록은 `state/replied.json`.

## 띠별 오늘 (매일 자동)

매일 06:40에 그날 일진을 계산하고, Claude가 12띠 한 줄을 쓰고, 수묵 릴스를 만들어 두었다가 **07:30 정각**에 인스타 릴스와 스레드 타래로 올립니다. 시각은 Variables `DAILY_POST_AT`(예: `07:30`)으로 바꿀 수 있습니다. 수동 실행은 기다리지 않고 바로 올립니다.

1. **켜기:** Variables에 `DAILY` = `on`. 끌 때는 `off`.
2. **시험:** Actions → "띠별 오늘" → Run workflow → dry_run `true` (기본값). 끝나면 실행 화면 아래 Artifacts에서 영상(daily-reel)을 받아 볼 수 있습니다. 올리지는 않습니다.
3. **음악:** 인스타 토큰이 페이스북 로그인 토큰(`EAA…`)이면 인스타 음악을 검색해 자동으로 붙입니다. 최근 2주에 쓴 곡은 피합니다. 검색어는 Variables `DAILY_MUSIC_QUERIES`(쉼표로 구분)로 바꿀 수 있습니다. 인스타 로그인 토큰(`IGAA…`)이면 음악 없이 올라갑니다.
4. **동물 그림:** `reels/assets/animals/`에 12장을 넣으면 다음 날부터 들어갑니다(파일 이름은 그 폴더의 README).
5. **문장 규칙:** `scripts/daily_prompt.md`. 최근 7일 문장과 겹치면 다시 씁니다.
6. **모델:** Variables `DAILY_MODEL` = `opus`(기본) / `sonnet` / `haiku`.

- 영상은 `posts/daily/`에 올라가고(인스타가 가져가는 주소), 2주 지난 것은 지웁니다.
- 기록은 `state/daily_history.json`. 같은 날 두 번 올리지 않습니다.

## 게시물 승인하는 법

`posts/schedule.json`을 GitHub 웹에서 열고 연필 아이콘 → 올릴 항목의 `"approved": false`를 `true`로 → Commit.
그 시각이 지나면 30분 안에 올라갑니다. 뺄 것은 `false`로 두거나 항목을 지우면 됩니다.
문구를 고치고 싶으면 `text`를 바로 고치면 됩니다.

- `at`은 한국 시각입니다.
- 시각이 이틀 넘게 지난 항목은 올리지 않습니다(밀린 게 한꺼번에 올라가는 것 방지).
- 한 번 실행에 최대 3건만 올립니다.
- 실패하면 `state/posted.json`에 이유가 남고, 3번 실패한 항목은 더 시도하지 않습니다.

## 토큰 연장

인스타·스레드 장기 토큰은 60일이면 만료됩니다.
- 자동: Secrets에 `GH_PAT`(이 저장소 Secrets 쓰기 권한이 있는 GitHub 토큰)을 넣으면 매달 1일·15일에 알아서 연장합니다.
- 수동: `GH_PAT`을 안 넣으면 50일마다 새 토큰을 `IG_TOKEN`, `THREADS_TOKEN`에 다시 넣어 주세요.

## 폴더

| 경로 | 내용 |
|---|---|
| `posts/schedule.json` | 게시 일정과 문구, 승인 |
| `posts/p0*/` | 카드 이미지(1080×1350) |
| `state/posted.json` | 올린 기록(자동) |
| `scripts/post.py` | 게시 스크립트 |
| `scripts/reply.py`, `reply_persona.md` | 자동 답글과 구조 AI 말투 지침 |
| `reels/` | 수묵 릴스 렌더러(띠별 오늘), 한지·먹산·인장 자산, 동물 그림 자리 |
| `scripts/daily_run.py`, `daily_prompt.md` | 띠별 오늘 자동 실행과 문장 지침 |
| `tools/` | 카드 이미지 만드는 도구와 원고(spec.json) |
| `PLAN.md` | 첫 2주 운영 계획 |
