# autospec PoC 설계

## 개요

autospec은 Karpathy의 autoresearch에서 영감을 받은 시스템이다.
사람이 자연어로 작성한 도메인 문서를 기반으로, AI 에이전트가 자율적으로 서비스 코드를 작성하고 검증하는 루프를 구현한다.

### autoresearch와의 대응

| autoresearch | autospec |
|---|---|
| program.md (에이전트 지시) | .autospec/program.md |
| prepare.py (평가 함수, 수정 불가) | .autospec/eval.md + 빌드/테스트 파이프라인 |
| train.py (AI가 수정) | src/ (서비스 코드 + 테스트) |
| val_bpb (단일 평가 지표) | evaluation score (복합 지표) |
| uv run train.py (5분 훈련) | ./gradlew bootRun + API 호출 (로컬 검증) |

### PoC 범위

- 한 사이클만 실행 (루프 아님)
- 빈 뼈대 Spring Boot 앱에서 시작, AI가 로직을 채워넣는 시나리오
- Claude Code가 한 세션에서 수행
- 도메인: 할일 (TODO)

## 핵심 원칙

### 도메인 문서는 사람이 쓰는 자연어 문서다

- 기술 용어나 코드가 포함되지 않는다
- 기획자, PM, 신규 개발자 누구나 읽고 쓸 수 있다
- API 경로, 타입, 어노테이션 같은 것은 AI가 코드를 읽고 스스로 매핑한다

### 공통 스펙과 도메인 스펙은 분리한다

- common/: 모든 도메인에 적용되는 기술/인프라 규약
- domain/: 순수 비즈니스 규칙만
- 도메인 문서에 기술 얘기가 없고, 공통 스펙에 비즈니스 얘기가 없다

### 평가는 AI 바깥에 있어야 한다

- PoC에서는 Claude Code가 직접 수행하지만, 프로덕션에서는 orchestrator가 담당
- AI가 자기 결과를 자기가 채점하면 안 된다 (autoresearch에서 prepare.py가 수정 불가인 이유)

### Goal은 배포가 아니라 검증된 코드다

- 자율 루프의 목표는 evaluation score가 수렴할 때까지 코드 품질을 개선하는 것
- 프로덕션 배포는 사람이 판단. dev 환경 배포까지만 자동화 대상

## 프로젝트 구조

```
autospec-poc/
├── .autospec/
│   ├── program.md              ← AI 에이전트 행동 지침
│   ├── common/
│   │   ├── 기술스택.md          ← 언어, 프레임워크, 빌드 도구
│   │   ├── 응답규약.md          ← API 응답 형식, 에러 코드 체계
│   │   └── 인프라규약.md        ← DB 네이밍, 패키지 구조, 공통 규칙
│   ├── domain/
│   │   └── 할일.md             ← 할일 도메인 비즈니스 규칙
│   └── eval.md                 ← 평가 기준
│
├── src/main/java/com/example/todo/
│   ├── TodoApplication.java
│   ├── Todo.java               ← 엔티티 (필드만, 로직 없음)
│   ├── TodoRepository.java     ← JPA Repository (빈 인터페이스)
│   ├── TodoService.java        ← 빈 클래스
│   └── TodoController.java     ← 엔드포인트 뼈대만
│
├── src/test/java/...           ← AI가 생성
├── build.gradle
└── application.yaml
```

## .autospec/ 문서 상세

### program.md

AI 에이전트가 어떻게 행동해야 하는지 정의한다.

핵심 지시:
- common/ 문서를 먼저 읽고, domain/ 문서를 읽어라
- 소스 코드를 읽고 도메인 규칙과의 간극을 찾아라
- 간극을 메우기 위해 코드를 수정하고 테스트를 생성하라
- 로컬에서 서버를 띄우고 검증하라

수정 가능: src/main/java/**, src/test/java/**
수정 불가: .autospec/**, build.gradle, application.yaml

제약:
- 한 사이클 제한시간 10분
- 기존 public API 시그니처를 함부로 변경하지 않을 것
- 확신 없는 큰 변경보다 작은 확실한 변경을 우선할 것

### common/기술스택.md

기술 선택에 대한 규약:
- Java 17, Spring Boot 3.x, Gradle
- H2 인메모리 DB, JPA/Hibernate
- JUnit 5, Spring Boot Test

### common/응답규약.md

API 응답 형식에 대한 규약:
- 성공 시 데이터 직접 반환, 목록은 배열
- 생성 성공 201, 그 외 200
- 에러 시 status + message 형태
- 404 (없는 리소스), 400 (잘못된 입력), 500 (서버 오류)

### common/인프라규약.md

인프라/코드 규약:
- 패키지: com.example.{도메인}
- 테이블/컬럼: snake_case
- API 경로: 복수형 명사 (/api/todos)
- JSON 필드: camelCase
- 모든 엔티티에 생성일시
- ID는 Long 자동 생성

### domain/할일.md

순수 비즈니스 규칙:
- 할일의 상태 흐름: 대기 → 진행중 → 완료
- 완료된 할일은 상태 변경 불가
- 제목 필수, 빈 문자열 불가
- 마감일은 과거 날짜 불가
- 우선순위: 높음/보통/낮음, 기본값 보통

불변 규칙:
- 제목 없는 할일 생성 불가
- 완료된 할일 상태 변경 불가
- 존재하지 않는 할일 조회 시 적절한 응답
- 잘못된 상태 변경 거부

### eval.md

평가 기준:
- 빌드 성공
- 서버 정상 기동
- 기존 테스트 전체 통과
- 도메인 문서의 "절대 깨지면 안 되는 것들"이 테스트로 검증됨
- 도메인 문서의 시나리오가 실제로 동작함

## 뼈대 앱 상세

### 사람이 미리 만드는 것

Spring Boot 프로젝트 초기화:
- build.gradle (spring-boot-starter-web, spring-boot-starter-data-jpa, h2, spring-boot-starter-test)
- application.yaml (H2 설정, JPA ddl-auto: create-drop)
- TodoApplication.java (@SpringBootApplication)
- Todo.java (id, title, status, priority, dueDate, createdAt 필드만)
- TodoRepository.java (JpaRepository 인터페이스)
- TodoService.java (빈 클래스, @Service)
- TodoController.java (@RestController, @RequestMapping("/api/todos"), 빈 메서드)

### AI가 채우는 것

- TodoService: CRUD 로직, 상태 전이 검증, validation
- TodoController: 요청/응답 처리, 에러 핸들링
- DTO 클래스 (필요시 생성)
- 테스트 코드

## PoC 실행 시나리오

```
1. 사람: autospec-poc/ 프로젝트 준비 (뼈대 + .autospec/ 문서)

2. Claude Code 실행:
   ".autospec/program.md를 읽고 한 사이클을 수행하라"

3. Claude Code 수행 내역:
   a) .autospec/common/*.md 읽기 → 기술/인프라 규약 파악
   b) .autospec/domain/할일.md 읽기 → 비즈니스 규칙 파악
   c) src/ 소스 코드 읽기 → 빈 뼈대 확인
   d) 간극 목록 작성: "Service 로직 없음, validation 없음, 테스트 없음"
   e) 코드 작성: Service 로직 + Controller 응답 처리 + 테스트
   f) ./gradlew build 실행 → 빌드 및 테스트 통과 확인
   g) ./gradlew bootRun → 서버 기동
   h) curl/httpie로 API 호출 → 시나리오 동작 확인
   i) eval.md 기준으로 자체 평가
   j) 결과 보고

4. 사람: 결과 확인, AI가 생성한 코드 리뷰
```

## 프로덕션 확장 방향 (PoC 이후)

PoC에서 한 사이클이 검증되면:
- orchestrator 분리: 평가/판정을 AI 바깥으로
- 자율 루프: 여러 사이클 자동 반복
- mutation testing: pitest 연동으로 테스트 품질 자동 검증
- 도메인 추가: domain/ 폴더에 문서만 추가하면 확장
- 프로덕션 피드백: 에러 로그 → 자동 regression test + 패치
