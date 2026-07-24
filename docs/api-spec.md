# API 명세

## 공통 사항

구현 위치:

```text
api/index.py          - FastAPI 앱, 라우팅 (/api/generate, /api/evaluate, 정적 파일)
api/generate.py       - 문제 생성 로직 (요청 검증, OpenAI 호출, Langfuse 계측)
api/evaluate.py       - 평가 로직 (요청 검증, OpenAI 호출, Langfuse 계측)
api/observability.py  - Langfuse 클라이언트 초기화, 설정 여부 확인, flush 헬퍼
```

Vercel Python 런타임은 하나의 ASGI/WSGI 앱을 엔트리포인트로 사용합니다. `api/index.py`의 top-level `app` (FastAPI 인스턴스)이 모든 요청을 받아 `/api/generate`, `/api/evaluate`는 API 라우트로 처리하고, 나머지 경로는 `StaticFiles` 마운트로 프로젝트 루트의 정적 파일을 서빙합니다.

AI 제공자는 OpenAI로 통일합니다. 문제 생성과 평가 모두 OpenAI Responses API의 구조화된 JSON 출력(`json_schema`)을 사용합니다.

예상 환경 변수:

```text
OPENAI_API_KEY
OPENAI_MODEL
```

`OPENAI_MODEL`은 선택 값입니다. 설정하지 않으면 기본 모델(`gpt-5-mini`)을 사용합니다.

## POST /api/generate

선택한 Part 유형에 맞는 토익 스피킹 문제를 AI가 새로 생성합니다.

프론트엔드 호출 방식:

```js
fetch('/api/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ part: 'part3' })
})
```

### 요청

```json
{ "part": "part3" }
```

### 요청 필드

- `part`: `part3` 또는 `part5`

### 입력 검증

- `part`가 없음 → 400
- 지원하지 않는 `part` 값 → 400

권장 오류 형식:

```json
{ "error": "지원하지 않는 문제 유형입니다." }
```

### 성공 응답 (part3)

```json
{
  "part": "part3",
  "context": "당신은 친구와 저녁 식사 약속을 잡고 있습니다.",
  "dialogue": "Hi, are we still on for dinner this Friday? I was thinking we could try the new Italian place downtown around 7 PM.",
  "questions": [
    "What time does the speaker want to have dinner?",
    "Where does the speaker want to go?",
    "Why do you think the speaker chose that place? Explain your guess."
  ]
}
```

### 성공 응답 (part5)

```json
{
  "part": "part5",
  "situation": "안녕하세요, 저는 다음 주 화요일 오후 3시로 예약한 헤어 미용실 예약 건으로 전화드렸습니다. 그런데 그 시간에 갑자기 회사 미팅이 잡혀서 예약을 다른 시간으로 옮기고 싶습니다. 가능한 시간을 확인해 주시고 다시 연락 부탁드립니다.",
  "problem": "화요일 오후 3시 미용실 예약을 다른 시간으로 변경해야 함"
}
```

### 응답 규칙

- Part3의 `questions`는 항상 3개입니다.
- 생성되는 상황은 실제 토익 스피킹 시험과 유사한 일상적 소재(약속, 예약, 쇼핑, 여행, 사내 공지 등)를 사용합니다.
- 매 요청마다 이전과 다른 상황을 생성하도록 프롬프트에 다양성을 지시합니다.
- 모델이 반환한 원본 텍스트를 그대로 검증 없이 클라이언트에 보내지 않습니다.

## POST /api/evaluate

사용자의 텍스트 답변을 문제 맥락과 비교해 평가합니다. Part3는 질문 1개 + 답변 1개 단위로 호출합니다(문항마다 개별 평가).

프론트엔드 호출 방식:

```js
fetch('/api/evaluate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    part: 'part3',
    context: '...',
    dialogue: '...',
    question: 'What time does the speaker want to have dinner?',
    userAnswer: 'The speaker wants to have dinner at 7 PM this Friday.'
  })
})
```

### 요청 (part3)

```json
{
  "part": "part3",
  "context": "당신은 친구와 저녁 식사 약속을 잡고 있습니다.",
  "dialogue": "Hi, are we still on for dinner this Friday? ...",
  "question": "What time does the speaker want to have dinner?",
  "userAnswer": "The speaker wants to have dinner at 7 PM this Friday."
}
```

### 요청 (part5)

```json
{
  "part": "part5",
  "situation": "안녕하세요, 저는 다음 주 화요일...",
  "problem": "화요일 오후 3시 미용실 예약을 다른 시간으로 변경해야 함",
  "userAnswer": "I understand you need to reschedule your appointment. ..."
}
```

### 요청 필드

- `part`: `part3` 또는 `part5`
- part3: `context`, `dialogue`, `question`, `userAnswer`
- part5: `situation`, `problem`, `userAnswer`

### 입력 검증

- `part`가 없거나 지원하지 않는 값 → 400
- part3인데 `question`, `dialogue`, `context` 중 하나라도 비어 있음 → 400
- part5인데 `situation`, `problem` 중 하나라도 비어 있음 → 400
- `userAnswer`가 비어 있음 → 400
- `userAnswer`에 영어 알파벳이 전혀 없음(한글만 입력 등) → 400

권장 오류 형식:

```json
{ "error": "답변을 입력해 주세요." }
```

### 성공 응답

```json
{
  "score": 78,
  "contentScore": 80,
  "grammarScore": 75,
  "vocabularyScore": 78,
  "sampleAnswer": "The speaker wants to have dinner at 7 PM this Friday at a new Italian restaurant downtown.",
  "feedback": "질문에서 요구한 시간 정보는 정확히 답했지만 장소에 대한 설명이 다소 부족합니다.",
  "improvements": [
    {
      "original": "at 7",
      "suggestion": "at 7 PM",
      "reason": "오전/오후 구분을 명시하면 더 정확한 답변이 됩니다."
    }
  ]
}
```

### 응답 규칙

- 모든 점수 필드는 0부터 100 사이의 정수여야 합니다.
- `sampleAnswer`는 해당 문항에 대한 모범 답안 예시입니다.
- `improvements`는 빈 배열일 수 있습니다.
- JSON 필드 값 안에는 Markdown을 넣지 않습니다.
- 모델이 반환한 원본 텍스트를 그대로 클라이언트에 보내지 않습니다.

## 평가 프롬프트 요구사항

모델에는 다음 정보를 전달해야 합니다.

- Part 유형
- 문제 맥락(상황, 대화문 또는 문제 설명)
- 평가 대상 질문(Part3) 또는 문제 요약(Part5)
- 사용자 답변
- JSON 출력 스키마
- 평가 원칙

반드시 포함할 평가 원칙:

```text
실제 토익 스피킹 채점 기준(내용의 적절성, 문법, 어휘, 답변 구성)에 따라 평가하세요.
텍스트 답변이므로 발음, 억양, 유창성은 평가하지 마세요.
```

## 실패 처리

클라이언트에 보여줄 기본 실패 메시지:

- 생성 실패: `문제를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.`
- 평가 실패: `평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.`

실패 상황:

- AI 제공자 요청 실패
- AI 제공자가 잘못된 JSON 반환
- 네트워크 타임아웃
- API 키 누락
- 예상하지 못한 서버 오류

## HTTP 상태 코드

- `200`: 성공
- `400`: 잘못된 사용자 입력
- `500`: 생성/평가 실패

## GET /api/generate, GET /api/evaluate

GET 요청은 지원하지 않습니다. `405`와 함께 POST 사용 안내 메시지를 반환합니다.

## Langfuse 관측

`/api/generate`, `/api/evaluate` 호출은 Langfuse로 trace됩니다. Self-hosted Langfuse 인스턴스를 사용합니다.

구현 위치: `api/observability.py`

동작 방식:

- `api/generate.py`, `api/evaluate.py`는 각각 `run_generation`, `run_evaluation` 전체를 `@observe`로 감싼 span 하나로 기록합니다.
- 그 안에서 실제 OpenAI 호출 구간을 `generation` 타입 관측으로 별도 기록합니다. 모델명, 시스템 프롬프트, 사용자 프롬프트(Part3/Part5 맥락 포함), 모델 출력, 토큰 사용량(`usage_details`)을 남깁니다.
- `/api/evaluate`는 추가로 종합 점수를 0~1 스케일로 정규화해 `score`로 함께 기록합니다.
- 요청 처리가 끝나면 항상 `flush()`를 호출합니다. Vercel Serverless Functions는 요청마다 짧게 실행되므로, 백그라운드 배치 전송에만 의존하면 프로세스 종료 시 이벤트가 유실될 수 있기 때문입니다.

Fail-safe 정책:

- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`가 설정되지 않으면 Langfuse 관련 코드를 전혀 실행하지 않고 기존 로직만 수행합니다.
- Langfuse 인스턴스에 연결할 수 없거나 전송이 실패해도 예외를 삼키고 로그만 남깁니다. 트레이싱 실패가 문제 생성/평가 API 자체의 성공 여부에 영향을 주지 않습니다.

예상 환경 변수:

```text
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_BASE_URL
```

`LANGFUSE_BASE_URL`은 self-hosted 인스턴스 주소입니다. Vercel 배포 환경(외부 클라우드)에서도 도달 가능하도록 공인 IP 또는 도메인을 사용합니다. Langfuse Cloud를 사용하는 경우 생략하면 기본 EU 리전을 사용합니다.

Vercel Preview/Production 환경변수에도 `OPENAI_API_KEY`와 동일하게 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`을 등록해야 배포 환경에서도 trace가 기록됩니다.

주의사항:

- API 키(`LANGFUSE_SECRET_KEY` 포함)는 코드와 문서에 직접 쓰지 않고 환경 변수로만 관리합니다.
- 사용자의 문제 맥락과 답변, AI 평가 결과가 Langfuse trace에 그대로 기록되므로, 학습 데이터로 취급될 수 있는 내용이라는 점을 인지합니다.
- self-hosted 인스턴스가 사설 IP(예: 사내망 대역)만 가리키면 Vercel에서 절대 도달할 수 없으므로, 배포 환경에서 쓰려면 반드시 공인 IP/도메인으로 접근 가능해야 합니다.
