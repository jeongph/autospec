# autospec Orchestrator 설계

## 개요

autospec PoC에서 한 사이클이 검증되었다. 이 설계는 여러 사이클을 자동으로 반복하는 orchestrator를 정의한다.

### 핵심 원칙

- **AI는 매 사이클마다 스스로 다음 작업을 결정한다** — 할 일 목록을 미리 정하지 않는다
- **평가는 AI 바깥에서 수행한다** — orchestrator가 빌드/테스트 결과를 기계적으로 판정한다
- **이전 사이클 결과를 다음 사이클에 전달한다** — AI가 같은 작업을 반복하지 않도록 한다
- **추가 비용 없이 동작한다** — Claude API 대신 Claude Code CLI(`claude -p`)를 사용한다

## 구조

```
.autospec/
├── program.md              ← (기존) AI 에이전트 지침
├── common/                 ← (기존) 공통 스펙
├── domain/                 ← (기존) 도메인 문서
├── eval.md                 ← (기존) 평가 기준
├── orchestrator.py         ← 루프 관리 (메인 진입점)
├── evaluator.py            ← 빌드/테스트 결과 파싱, 점수 산출
├── history.py              ← runs/ 기록 읽기/쓰기
└── runs/                   ← 사이클 실행 기록
    ├── run-001.md
    └── run-002.md
```

### 역할 분리

| 컴포넌트 | 역할 | AI 개입 |
|---|---|---|
| orchestrator.py | 루프 관리, claude -p 호출, 종료 판단 | 없음 |
| evaluator.py | gradlew build 실행, 테스트 결과 파싱, accept/reject 판정 | 없음 |
| history.py | runs/ 기록 쓰기/읽기, 이전 결과 요약 | 없음 |
| claude -p | 코드 수정, 테스트 생성, 커밋 | AI가 수행 |

## 실행 흐름

```
$ python orchestrator.py examples/spring-boot-todo

[사이클 N]
1. history.py: 이전 run 기록 읽기
2. orchestrator.py: claude -p 호출
   프롬프트 구성:
   - program.md 내용
   - 이전 사이클 결과 요약 (history.py가 제공)
3. AI가 도메인 문서를 읽고 간극을 찾아 코드 수정 + 테스트 생성 + 커밋
4. evaluator.py: ./gradlew build 실행 → 결과 파싱
5. 판정:
   - reject → git reset --hard HEAD~1
   - accept → 유지
6. history.py: runs/run-{N}.md에 결과 기록
7. 종료 조건 확인 → 계속 / 중단
```

## evaluator.py — 평가 로직

### 수집하는 메트릭

```python
{
    "build_success": True/False,       # gradlew build 결과
    "test_total": 25,                  # 전체 테스트 수
    "test_passed": 25,                 # 통과 테스트 수
    "test_failed": 0,                  # 실패 테스트 수
    "test_diff": +3,                   # 이전 대비 테스트 증감
}
```

### 판정 규칙

- 빌드 실패 → reject (git reset)
- 테스트 실패 있음 → reject (git reset)
- 테스트 수 감소 → reject (git reset)
- 빌드 성공 + 전체 통과 + 테스트 수 유지/증가 → accept

### 테스트 결과 파싱

Gradle의 JUnit XML 리포트(`build/test-results/test/*.xml`)를 파싱하여 테스트 수와 통과/실패를 추출한다.

## history.py — 사이클 간 컨텍스트

### runs/run-001.md 형식

```markdown
# Run 001
- 사이클: 1
- 판정: accept
- 빌드: 성공
- 테스트: 25/25 (이전 대비 +3)
- AI 커밋 메시지: "feat: 상태 전이 검증 추가"
- 변경 파일: TodoService.java, TodoServiceTest.java
```

### 이전 결과 요약 생성

history.py는 최근 N개의 run 기록을 읽어 AI에게 전달할 요약을 생성한다.

```
이전 사이클 결과:
- Run 001: 금액 검증 추가, 테스트 8개 → 11개, accept
- Run 002: 상태 전이 검증 추가, 테스트 11개 → 18개, accept
- Run 003: 에러 응답 형식 수정, 테스트 18개 → 18개, accept (개선 없음)
```

AI는 이 요약을 보고 "뭘 이미 했고 뭘 아직 안 했는지" 판단한다.

## orchestrator.py — 루프 관리

### Claude Code CLI 호출

```python
prompt = f"""
.autospec/program.md를 읽고 한 사이클을 수행하라.

{previous_runs_summary}

주의:
- 이전 사이클에서 이미 수행한 작업은 반복하지 마라
- 아직 해결되지 않은 간극을 찾아서 해결하라
- 작업이 끝나면 반드시 커밋하라
"""

result = subprocess.run(
    ["claude", "-p", prompt, "--allowedTools", "Edit,Write,Bash,Read,Glob,Grep"],
    cwd=project_root,
    capture_output=True, text=True,
    timeout=600  # 10분 제한
)
```

### 종료 조건

| 조건 | 기본값 | 의미 |
|---|---|---|
| max_cycles | 10 | 최대 사이클 수 |
| max_consecutive_failures | 3 | 연속 실패 시 중단 |
| max_no_improvement | 2 | 연속 개선 없으면 수렴으로 판단 |

### reject 시 롤백

AI는 매 사이클마다 커밋하므로, 실패 시 마지막 커밋만 되돌린다:

```python
subprocess.run(["git", "reset", "--hard", "HEAD~1"])
```

## 실행 예시

```
$ python orchestrator.py examples/spring-boot-todo

autospec orchestrator v0.1
프로젝트: /home/jeonguk/dev/lighthouse/repositories/autospec/examples/spring-boot-todo
최대 사이클: 10

[사이클 1/10]
  AI 실행 중... (timeout: 10분)
  AI 완료: 커밋 발견 "feat: 할일 삭제 기능 추가"
  평가: 빌드 성공, 테스트 28/28 (+3)
  판정: accept ✓

[사이클 2/10]
  AI 실행 중... (timeout: 10분)
  AI 완료: 커밋 발견 "feat: 할일 수정 기능 추가"
  평가: 빌드 성공, 테스트 33/33 (+5)
  판정: accept ✓

[사이클 3/10]
  AI 실행 중... (timeout: 10분)
  AI 완료: 커밋 발견 "fix: 마감일 검증 경계값 수정"
  평가: 빌드 성공, 테스트 35/35 (+2)
  판정: accept ✓

[사이클 4/10]
  AI 실행 중... (timeout: 10분)
  AI 완료: 커밋 발견 "refactor: 에러 메시지 개선"
  평가: 빌드 성공, 테스트 35/35 (+0)
  판정: accept (개선 없음 1/2)

[사이클 5/10]
  AI 실행 중... (timeout: 10분)
  AI 완료: 커밋 없음
  평가: 변경 없음
  판정: 수렴 (개선 없음 2/2)

완료: 5 사이클, 4 accept, 0 reject
최종 테스트: 35/35
```
