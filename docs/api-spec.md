# API 명세

## POST /api

사용자의 영어 답변을 한국어 원문과 비교해 평가합니다.

구현 위치:

```text
api/index.py
```

프론트엔드 호출 방식:

```js
fetch('/api', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    level: 'beginner',
    koreanSentence: '나는 주말마다 친구를 만난다.',
    userAnswer: 'I meet my friend every weekend.'
  })
})
```

## 요청

```json
{
  "level": "beginner",
  "koreanSentence": "나는 주말마다 친구를 만난다.",
  "userAnswer": "I meet my friend every weekend."
}
```

## 요청 필드

- `level`: `beginner` 또는 `intermediate`
- `koreanSentence`: 사용자에게 제시된 한국어 원문
- `userAnswer`: 사용자가 작성한 영어 답변

## 입력 검증

클라이언트에서 이미 검증하더라도 API에서 다시 검증해야 합니다.

잘못된 요청:

- `level`이 없음
- 지원하지 않는 `level`
- 비어 있는 `koreanSentence`
- 비어 있는 `userAnswer`
- 한글만 입력된 `userAnswer`

권장 오류 형식:

```json
{
  "error": "영어 문장을 입력해 주세요."
}
```

## 성공 응답

```json
{
  "score": 85,
  "meaningScore": 90,
  "grammarScore": 85,
  "naturalnessScore": 80,
  "correctedSentence": "I meet my friends every weekend.",
  "feedback": "전체적인 의미와 문법은 정확합니다.",
  "mistakes": [
    {
      "original": "my friend",
      "correction": "my friends",
      "reason": "일반적으로 여러 친구를 만난다는 의미이므로 복수형이 더 자연스럽습니다."
    }
  ]
}
```

## 응답 규칙

- 모든 점수 필드는 0부터 100 사이의 정수여야 합니다.
- `correctedSentence`는 가장 추천할 만한 영어 문장입니다.
- 사용자의 문장이 이미 정확하고 자연스럽다면 `correctedSentence`는 `userAnswer`와 같을 수 있습니다.
- `mistakes`는 빈 배열일 수 있습니다.
- JSON 필드 값 안에는 Markdown을 넣지 않습니다.
- 모델이 반환한 원본 텍스트를 그대로 클라이언트에 보내지 않습니다.

## AI 제공자

MVP에서는 OpenAI 또는 Gemini를 사용할 수 있습니다. 구현 시 별도 지정이 없다면 구조화된 JSON 응답을 강제하기 쉬운 OpenAI를 우선 사용합니다.

백엔드는 Vercel Serverless Functions의 Python으로 구현합니다. 필요한 패키지는 `requirements.txt`에 정의합니다.

예상 환경 변수:

```text
OPENAI_API_KEY
```

나중에 Gemini를 선택하는 경우:

```text
GEMINI_API_KEY
```

## Langfuse 관측

Langfuse 연동은 MVP 필수 기능은 아니지만, AI 평가 품질을 확인하기 위한 우선 확장 항목입니다.

관측 대상:

- `/api` 요청
- 난이도
- 한국어 원문
- 사용자 답변
- AI 평가 결과
- 오류와 JSON 파싱 실패
- 응답 시간

주의사항:

- 사용자의 원문과 답변은 학습 데이터가 될 수 있으므로, 추적 범위와 저장 정책을 명세에 남깁니다.
- API 키는 환경 변수로만 관리합니다.
- Langfuse 구현 전에는 최신 공식 문서를 확인합니다.

예상 환경 변수:

```text
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_HOST
```

## 평가 프롬프트 요구사항

모델에는 다음 정보를 전달해야 합니다.

- 난이도
- 한국어 원문
- 사용자 답변
- JSON 출력 스키마
- 평가 원칙

반드시 포함할 평가 원칙:

```text
문법적으로 정확하고 자연스러운 문장은 수정하지 마세요. 모범 답안과 표현이 다르다는 이유만으로 감점하지 마세요.
```

프롬프트에는 다음 내용을 명시해야 합니다.

- 영작에는 여러 개의 올바른 답변이 있을 수 있습니다.
- 모범 답안과 글자 단위로 비교해 채점하지 않습니다.
- 의미 전달, 문법, 자연스러움을 각각 평가합니다.
- 올바른 대체 표현은 그대로 인정합니다.
- 응답은 반드시 지정된 스키마와 일치하는 유효한 JSON만 반환합니다.

## 실패 처리

클라이언트에 보여줄 기본 실패 메시지:

```text
평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.
```

실패 상황:

- AI 제공자 요청 실패
- AI 제공자가 잘못된 JSON 반환
- 네트워크 타임아웃
- API 키 누락
- 예상하지 못한 서버 오류

## HTTP 상태 코드

- `200`: 평가 성공
- `400`: 잘못된 사용자 입력
- `500`: 평가 실패

## GET /api

브라우저 주소창에서 API 엔드포인트를 열었을 때 501 오류가 뜨지 않도록 상태 확인용 JSON을 반환합니다.

예상 응답:

```json
{
  "ok": true,
  "service": "TranslateUp evaluation API",
  "message": "이 엔드포인트는 POST 요청으로 영작 답변을 평가합니다."
}
```

실제 평가는 반드시 `POST /api`로 호출합니다.
