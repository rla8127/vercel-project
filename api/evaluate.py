import json
import os
import re
from http.server import BaseHTTPRequestHandler


ALLOWED_LEVELS = {"beginner", "intermediate"}

EVALUATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "score",
        "meaningScore",
        "grammarScore",
        "naturalnessScore",
        "correctedSentence",
        "feedback",
        "mistakes",
    ],
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "meaningScore": {"type": "integer", "minimum": 0, "maximum": 100},
        "grammarScore": {"type": "integer", "minimum": 0, "maximum": 100},
        "naturalnessScore": {"type": "integer", "minimum": 0, "maximum": 100},
        "correctedSentence": {"type": "string"},
        "feedback": {"type": "string"},
        "mistakes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["original", "correction", "reason"],
                "properties": {
                    "original": {"type": "string"},
                    "correction": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def has_korean(text):
    return bool(re.search(r"[ㄱ-ㅎㅏ-ㅣ가-힣]", text or ""))


def has_english(text):
    return bool(re.search(r"[A-Za-z]", text or ""))


def clamp_score(value):
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, number))


def normalize_result(payload, user_answer):
    mistakes = payload.get("mistakes")
    if not isinstance(mistakes, list):
        mistakes = []

    normalized_mistakes = []
    for mistake in mistakes:
        if not isinstance(mistake, dict):
            continue
        normalized_mistakes.append(
            {
                "original": str(mistake.get("original", "")),
                "correction": str(mistake.get("correction", "")),
                "reason": str(mistake.get("reason", "")),
            }
        )

    corrected = str(payload.get("correctedSentence") or user_answer)
    feedback = str(payload.get("feedback") or "평가 결과를 확인했습니다.")

    return {
        "score": clamp_score(payload.get("score")),
        "meaningScore": clamp_score(payload.get("meaningScore")),
        "grammarScore": clamp_score(payload.get("grammarScore")),
        "naturalnessScore": clamp_score(payload.get("naturalnessScore")),
        "correctedSentence": corrected,
        "feedback": feedback,
        "mistakes": normalized_mistakes,
    }


def validate_body(body):
    level = str(body.get("level", "")).strip()
    korean_sentence = str(body.get("koreanSentence", "")).strip()
    user_answer = str(body.get("userAnswer", "")).strip()

    if not level:
        return None, "난이도를 선택해 주세요."
    if level not in ALLOWED_LEVELS:
        return None, "지원하지 않는 난이도입니다."
    if not korean_sentence:
        return None, "한국어 문제가 없습니다."
    if not user_answer:
        return None, "영어 문장을 입력해 주세요."
    if has_korean(user_answer) and not has_english(user_answer):
        return None, "영어로 답변을 작성해 주세요."

    return {
        "level": level,
        "koreanSentence": korean_sentence,
        "userAnswer": user_answer,
    }, None


def build_prompt(data):
    return f"""
난이도: {data["level"]}
한국어 원문: {data["koreanSentence"]}
사용자 영어 답변: {data["userAnswer"]}

평가 기준:
1. 한국어 원문의 의미가 영어 답변에 잘 전달됐는지 평가하세요.
2. 영어 문법이 올바른지 평가하세요.
3. 실제 영어 표현으로 자연스러운지 평가하세요.
4. 영작에는 여러 개의 올바른 답변이 있을 수 있습니다.
5. 모범 답안과 글자 단위로 비교해 채점하지 마세요.
6. 문법적으로 정확하고 자연스러운 문장은 수정하지 마세요.
7. 모범 답안과 표현이 다르다는 이유만으로 감점하지 마세요.

응답은 지정된 JSON 스키마와 일치해야 합니다.
""".strip()


def evaluate_with_openai(data):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=25)
    model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "당신은 한국어 사용자를 위한 영어 영작 평가자입니다. "
                    "친절하지만 정확하게 평가하고, 올바른 대체 표현은 인정하세요. "
                    "JSON 외의 텍스트는 반환하지 마세요."
                ),
            },
            {"role": "user", "content": build_prompt(data)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "english_writing_evaluation",
                "schema": EVALUATION_SCHEMA,
                "strict": True,
            }
        },
        max_output_tokens=900,
    )

    output_text = getattr(response, "output_text", "")
    if not output_text:
        raise ValueError("Empty model response")

    return normalize_result(json.loads(output_text), data["userAnswer"])


class EvaluationHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        self._send_json(
            200,
            {
                "ok": True,
                "service": "TranslateUp evaluation API",
                "message": "이 엔드포인트는 POST 요청으로 영작 답변을 평가합니다.",
            },
        )

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body or "{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "요청 형식이 올바르지 않습니다."})
            return

        data, error = validate_body(body)
        if error:
            self._send_json(400, {"error": error})
            return

        try:
            result = evaluate_with_openai(data)
        except Exception:
            self._send_json(500, {"error": "평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."})
            return

        self._send_json(200, result)
