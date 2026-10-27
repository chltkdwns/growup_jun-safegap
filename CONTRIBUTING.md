# SafeGap 개발 가이드

## 0. 꼭 지킬 것
- main은 GitHub 규칙으로 보호됨 (6번 참고) → 반드시 PR + 다른 팀원 1명 승인
- 다른 사람과 같이 쓰는 브랜치에서는 `git push -f`(강제 푸시) 금지
- `.env`, API 키는 절대 커밋하지 않기 (한 번 올라가면 이력에 남음)
- 모델 가중치(`*.pt`), 데이터셋, 영상(`*.mp4`)은 깃에 올리지 않기 → 팀 드라이브 공유
- 하루 끝날 때 PR 올리기
- 충돌나면 혼자 풀지 말고 다 같이 해결하기

## 1. 처음 셋팅
```bash
gh repo clone chltkdwns/growup_jun-safegap
cd growup_jun-safegap
```

### backend · model (Python)
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # 값은 팀 채팅에서 받기
uvicorn backend.main:app --reload
```

### frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

## 2. 역할
| 이름 | 담당 | 폴더 |
|---|---|---|
| | 프론트엔드 | frontend/ |
| | 백엔드 · 깃 관리 | backend/ |
| | AI 모델 | model/ |

자기 폴더 밖 파일을 고칠 때는 먼저 팀에 말해 주세요.

## 3. 브랜치 규칙
| 브랜치 | 용도 | 규칙 |
|---|---|---|
| main | 항상 돌아가는 상태 | 직접 푸시 불가 (PR만) |
| feat/기능명 | 기능 개발 | 각자 생성 |
| fix/버그명 | 버그 수정 | 각자 생성 |

## 4. 작업 흐름 (매번 이 순서)
```bash
git switch main
git pull                       # 남의 작업 먼저 받기
git switch -c feat/기능명       # 내 브랜치 만들기
# ... 작업 ...
git add .
git commit -m "feat: 기능 설명"
git push -u origin feat/기능명
```
GitHub에서 **Compare & pull request** → PR 올리기 → 다른 팀원 1명 승인 → 머지

## 5. 커밋 메시지
| 타입 | 의미 |
|---|---|
| feat | 기능 추가 |
| fix | 버그 수정 |
| docs | 문서 |
| style | 서식 (동작 변경 없음) |
| refactor | 구조 정리 |

예: `feat: 앞차 거리 추정 추가`

## 6. main 브랜치 보호 규칙 (GitHub Ruleset)

`main`에는 아래 규칙이 걸려 있습니다. (Settings → Rulesets → `main 보호`)

| 규칙 | 의미 |
|---|---|
| Restrict deletions | main 브랜치 삭제 금지 |
| Require a pull request before merging | main에 직접 푸시 불가, 반드시 PR로만 합치기 |
| Required approvals: 1 | **작성자 말고 다른 팀원 1명이 Approve**해야 Merge 가능 |
| Block force pushes | main에 `git push -f` 불가 |

### PR 리뷰 방법
1. GitHub → **Pull requests** → 팀원 PR 열기
2. **Files changed** 탭에서 변경 내용 확인
3. 오른쪽 위 **Review changes** → **Approve** → **Submit review**
4. 승인되면 작성자가 **Merge pull request**