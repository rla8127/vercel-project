# TranslateUp

TranslateUp은 한국어 문장을 영어로 직접 작성하고 AI에게 의미 전달, 문법, 자연스러움을 평가받는 영작 학습 웹 서비스입니다.

## 주요 기능

- 초급/중급 난이도 선택
- 한국어 문제 기반 영어 답변 입력
- OpenAI API 기반 AI 영작 평가
- 종합 점수, 의미 전달, 문법, 자연스러움 점수 표시
- 추천 문장, 수정할 부분, 전체 피드백 제공
- 빈 입력, 한글만 입력, API 오류, 지연 상황 안내
- 모바일/데스크톱 반응형 UI

## 기술 스택

- Frontend: HTML, CSS, JavaScript
- Backend: Vercel Serverless Functions, Python
- AI API: OpenAI API
- Deploy: Vercel

## 프로젝트 구조

```text
index.html
css/
js/
api/
images/
data/
docs/
requirements.txt
vercel.json
README.md
```

## 로컬 실행

정적 화면만 확인하려면 다음 명령을 실행합니다.

```bash
python3 -m http.server 3000
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:3000
```

Python API까지 로컬에서 확인하려면 Python 3.12 이상의 가상환경을 만들고 의존성을 설치한 뒤, 그 가상환경을 활성화한 상태로 Vercel CLI를 실행합니다. (가상환경이 없으면 시스템 기본 Python으로 실행되어 오류가 날 수 있습니다.)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
vercel dev
```

## 환경 변수

OpenAI API 키는 코드에 직접 넣지 않습니다. 로컬에서는 `.env.local`에 설정하고, Vercel 배포 환경에서는 Project Settings의 Environment Variables에 설정합니다.

```text
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini
```

`OPENAI_MODEL`은 선택 값입니다. 설정하지 않으면 기본 모델을 사용합니다.

## 배포 방법

1. GitHub 저장소에 코드를 push합니다.
2. Vercel에서 GitHub 저장소를 연결합니다.
3. Environment Variables에 `OPENAI_API_KEY`를 추가합니다.
4. Vercel 배포를 실행합니다.
5. 배포 URL에서 메뉴 이동, 반응형 화면, AI 평가 기능을 확인합니다.

## 배포 URL

아직 배포 전입니다. Vercel 배포 후 URL을 여기에 기록합니다.

```text
TBD
```

## 서비스 기획서

서비스 기획과 SDD 문서는 `docs/` 폴더에 정리되어 있습니다.

- `docs/product-spec.md`
- `docs/user-flows.md`
- `docs/data-model.md`
- `docs/api-spec.md`
- `docs/implementation-plan.md`
- `docs/assignment-criteria.md`

## 보안 주의

- API 키를 코드, README, 스크린샷, 대화 로그에 노출하지 않습니다.
- 키 유출이 의심되면 즉시 폐기하고 재발급합니다.
- 노출된 키가 커밋에 포함됐다면 커밋 이력 정리도 필요합니다.
