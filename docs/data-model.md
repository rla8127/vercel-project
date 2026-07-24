# 데이터 모델

## 개요

MVP에서는 데이터베이스가 필요하지 않습니다. 문제는 매 요청마다 AI가 생성하며 저장하지 않습니다. 평가 결과도 요청 시점에 생성하고 저장하지 않습니다. 클라이언트 메모리(JS 상태)에서만 현재 문제와 결과를 유지합니다.

## 엔티티

### PartType

지원하는 토익 스피킹 문제 유형입니다.

```js
/**
 * PartType
 * "part3" | "part5"
 */
```

### GeneratedQuestion (Part3)

AI가 생성한 Part3 문제 세트입니다.

```js
/**
 * GeneratedQuestionPart3
 * part: "part3"
 * context: string       // 상황 설명 (예: "당신은 친구와 저녁 약속을 잡고 있습니다.")
 * dialogue: string       // 짧은 대화문 또는 안내문
 * questions: string[]    // 질문 3개
 */
```

### GeneratedQuestion (Part5)

AI가 생성한 Part5 문제입니다.

```js
/**
 * GeneratedQuestionPart5
 * part: "part5"
 * situation: string      // 문제 상황 설명 (음성 메시지 상황을 텍스트로 표현)
 * problem: string         // 핵심 문제 요약
 */
```

### GenerateRequest

클라이언트에서 `/api/generate`로 보내는 요청입니다.

```js
/**
 * GenerateRequest
 * part: "part3" | "part5"
 */
```

### EvaluateRequest (Part3)

질문 1개에 대한 평가 요청입니다. Part3는 질문마다 개별 평가합니다.

```js
/**
 * EvaluateRequestPart3
 * part: "part3"
 * context: string
 * dialogue: string
 * question: string       // 평가 대상 질문 1개
 * userAnswer: string
 */
```

### EvaluateRequest (Part5)

```js
/**
 * EvaluateRequestPart5
 * part: "part5"
 * situation: string
 * problem: string
 * userAnswer: string
 */
```

### EvaluationResult

`/api/evaluate`가 반환하는 구조화된 평가 결과입니다. Part3, Part5 공통 구조를 사용합니다.

```js
/**
 * EvaluationResult
 * score: number              // 종합 점수 (0-100)
 * contentScore: number       // 내용 적절성/완결성 점수 (0-100)
 * grammarScore: number       // 문법 점수 (0-100)
 * vocabularyScore: number    // 어휘 점수 (0-100)
 * sampleAnswer: string       // 모범 답안 예시
 * feedback: string           // 전체 피드백
 * improvements: EvaluationImprovement[]
 *
 * EvaluationImprovement
 * original: string
 * suggestion: string
 * reason: string
 */
```

점수 필드는 0부터 100 사이의 정수입니다.

## 저장 정책

MVP에서 저장하지 않는 것:

- 사용자 테이블
- 세션 테이블
- 생성된 문제 테이블
- 저장된 평가 결과 테이블
- 데이터베이스

향후 확장 후보:

- 사용자 계정
- 문제 풀이 기록 및 히스토리
- 음성 답변 및 발음 평가 (마이크 녹음 도입 시)
- Part 1, 2, 4 확장
