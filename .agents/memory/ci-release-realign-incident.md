---
name: ci-release-realign-incident
description: "2026-06-19 CI/release untangle — main-only release-please, release-dev.yml lingered on main, automerge runaway cut wrong tags"
metadata: 
  node_type: memory
  type: project
  originSessionId: a4836c2e-6905-4ad4-8d03-38fb94ff017b
---

2026-06-19 ha-apps CI/release 재설계. 목표 모델: **main 단일 release-please + dev 통합 전용 + sync-dev back-merge**. SPEC.md / tasks/plan.md 참조.

**근본 원인 (검증됨):**
- `67ec18c`가 `release-dev.yml`을 dev에서만 지우고 **origin/main엔 남겨**, main에서 `release.yml`+`release-dev.yml`이 release-please **이중 실행**.
- main 매니페스트가 실제 config.yaml보다 뒤처짐(유령 릴리스: config는 올랐으나 태그 없음). `automerge-release.yml`이 낡은 매니페스트 기반 release PR을 자동머지하며 **잘못된 태그를 계속 생성**(폭주: livekit 0.32.0, nemo-asr-cpp 0.16.0까지 제안).

**긴급 봉쇄 (모두 가역):** `gh workflow disable` → release.yml / automerge-release.yml / "Release (dev)". 폭주 PR #336·#322 close. → 재활성 전까지 자동 릴리스 정지 상태.

**버전 정합 규칙 = `max(dev 코드, main 태그)`** (main이 봉쇄 중 0.3.1/0.4.1/0.9.1/0.2.2 태그를 이미 잘랐기 때문, 그 아래로 내려가면 release-please가 기존 태그 재생성 시도):
livekit 0.9.0 · nemotron-asr-c 0.7.0 · nemo-asr-cpp 0.10.0 · supertonic 2.4.0 · voiceprint **0.9.1** · wardrowbe 4.0.0 · zensical **0.2.2**.

**RESOLVED 2026-06-19.** PR #247 머지(fcd3887)로 정본이 main에 도달 → release-dev.yml + 고아 dev config 삭제됨. main config==manifest 7/7 정본 일치. dev는 protection 임시해제→`git reset --hard origin/main` force-push→protection 복원으로 main에 reset(dev-only 93커밋은 전부 chore noise, 고유 코드 0). release.yml + automerge-release.yml 재활성 완료; dispatch 결과 release-please 제안 0건(정상, repo 스코프만 변경). main=dev (0 0).

**교훈/주의**: ① dev는 protected(force_push:false) — reset하려면 protection JSON 백업→allow_force_pushes=true→push→복원. ② release-please 매니페스트가 config.yaml과 어긋나면 version-check(ci.yml)가 PR에서 차단(이번에 추가). ③ 워크플로를 한 브랜치에서만 지우면 다른 브랜치에 잔존하니 `gh workflow list --all`로 항상 확인. ④ **release-please는 버전 경계를 매니페스트가 아니라 git 태그/Release로 판단** — 정본 버전 태그가 없으면(유령 릴리스) 마지막 실제 태그까지 거슬러 전 이력을 재계산해 잘못된 큰 버전(예 wardrowbe 5.0.0, livekit 0.10.0)을 제안. **해결: 정본 태그 백필** `gh release create <slug>-v<ver> --target main` (OPEN-1 "백필 안 함"을 뒤집음 — livekit-wakeword-v0.9.0·nemo-asr-cpp-v0.10.0·wardrowbe-v4.0.0 생성). ⑤ 제목 공백(`chore( slug)`)은 release-please 렌더링 quirk(config 패턴은 정상) — squash 머지 시 `--subject "chore(slug): ..."`로 정정. ⑥ **최종: 7앱 config==manifest==태그 3자 일치, sync-dev back-merge 실동작 success 검증, main=dev.** [[deployment-facts]] [[release-please-squash-gotcha]]
