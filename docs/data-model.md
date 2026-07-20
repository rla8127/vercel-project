# 데이터 모델

## 개요

MVP에서는 데이터베이스가 필요하지 않습니다. 문제는 프로젝트 안의 정적 JSON 파일에 저장합니다. 평가 결과는 요청 시점에 생성하고 저장하지 않습니다.

## 엔티티

### Exercise

하나의 한국어 영작 문제를 나타냅니다.

```js
/**
 * Exercise
 * id: number
 * level: "beginner" | "intermediate" | "advanced"
 * sentence: string
 * exampleAnswer?: string
 */
```

MVP에서 사용하는 난이도:

- `beginner`
- `intermediate`

`advanced`는 향후 확장을 위해 타입에는 둘 수 있지만, 명시적으로 요청받기 전까지 MVP 화면에는 노출하지 않습니다.

### EvaluationRequest

클라이언트에서 `/api/evaluate`로 보내는 요청입니다.

```js
/**
 * EvaluationRequest
 * level: "beginner" | "intermediate"
 * koreanSentence: string
 * userAnswer: string
 */
```

### EvaluationResult

`/api/evaluate`가 반환하는 구조화된 평가 결과입니다.

```js
/**
 * EvaluationResult
 * score: number
 * meaningScore: number
 * grammarScore: number
 * naturalnessScore: number
 * correctedSentence: string
 * feedback: string
 * mistakes: EvaluationMistake[]
 *
 * EvaluationMistake
 * original: string
 * correction: string
 * reason: string
 */
```

점수 필드는 0부터 100 사이의 정수입니다.

## 정적 문제 데이터

권장 위치:

```text
data/exercises.json
```

예시:

```json
[
  {
    "id": 1,
    "level": "beginner",
    "sentence": "나는 매일 아침 커피를 마신다.",
    "exampleAnswer": "I drink coffee every morning."
  },
  {
    "id": 2,
    "level": "beginner",
    "sentence": "그녀는 어제 영화를 보았다.",
    "exampleAnswer": "She watched a movie yesterday."
  },
  {
    "id": 3,
    "level": "intermediate",
    "sentence": "나는 시간을 절약할 수 있기 때문에 온라인 쇼핑을 선호한다.",
    "exampleAnswer": "I prefer shopping online because it saves me time."
  }
]
```

## 저장 정책

MVP에서 저장하지 않는 것:

- 사용자 테이블
- 세션 테이블
- 저장된 평가 결과 테이블
- 데이터베이스

향후 확장 후보:

- 사용자
- 문제 풀이 기록
- 저장된 피드백
- 학습 진행률
