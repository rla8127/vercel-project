import json
import os
import re

from observability import flush_langfuse, get_langfuse_client, is_configured


ALLOWED_PARTS = {"part3", "part5"}

EVALUATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "score",
        "contentScore",
        "grammarScore",
        "vocabularyScore",
        "sampleAnswer",
        "feedback",
        "improvements",
    ],
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "contentScore": {"type": "integer", "minimum": 0, "maximum": 100},
        "grammarScore": {"type": "integer", "minimum": 0, "maximum": 100},
        "vocabularyScore": {"type": "integer", "minimum": 0, "maximum": 100},
        "sampleAnswer": {"type": "string"},
        "feedback": {"type": "string"},
        "improvements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["original", "suggestion", "reason"],
                "properties": {
                    "original": {"type": "string"},
                    "suggestion": {"type": "string"},
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
    improvements = payload.get("improvements")
    if not isinstance(improvements, list):
        improvements = []

    normalized_improvements = []
    for item in improvements:
        if not isinstance(item, dict):
            continue
        normalized_improvements.append(
            {
                "original": str(item.get("original", "")),
                "suggestion": str(item.get("suggestion", "")),
                "reason": str(item.get("reason", "")),
            }
        )

    sample_answer = str(payload.get("sampleAnswer") or user_answer)
    feedback = str(payload.get("feedback") or "평가 결과를 확인했습니다.")

    return {
        "score": clamp_score(payload.get("score")),
        "contentScore": clamp_score(payload.get("contentScore")),
        "grammarScore": clamp_score(payload.get("grammarScore")),
        "vocabularyScore": clamp_score(payload.get("vocabularyScore")),
        "sampleAnswer": sample_answer,
        "feedback": feedback,
        "improvements": normalized_improvements,
    }


def validate_body(body):
    part = str(body.get("part", "")).strip()
    user_answer = str(body.get("userAnswer", "")).strip()

    if not part:
        return None, "문제 유형을 선택해 주세요."
    if part not in ALLOWED_PARTS:
        return None, "지원하지 않는 문제 유형입니다."

    if part == "part3":
        context = str(body.get("context", "")).strip()
        dialogue = str(body.get("dialogue", "")).strip()
        question = str(body.get("question", "")).strip()
        if not context or not dialogue or not question:
            return None, "문제 정보가 없습니다."
        data = {
            "part": part,
            "context": context,
            "dialogue": dialogue,
            "question": question,
        }
    else:
        situation = str(body.get("situation", "")).strip()
        problem = str(body.get("problem", "")).strip()
        if not situation or not problem:
            return None, "문제 정보가 없습니다."
        data = {
            "part": part,
            "situation": situation,
            "problem": problem,
        }

    if not user_answer:
        return None, "답변을 입력해 주세요."
    if has_korean(user_answer) and not has_english(user_answer):
        return None, "영어로 답변을 작성해 주세요."

    data["userAnswer"] = user_answer
    return data, None


def build_prompt(data):
    if data["part"] == "part3":
        problem_block = f"""
상황: {data["context"]}
대화문: {data["dialogue"]}
질문: {data["question"]}
""".strip()
        guidance = (
            "이 답변은 위 질문 하나에 대한 답입니다. "
            "질문에서 요구하는 정보를 정확하고 완결성 있게 전달했는지 평가하세요."
        )
    else:
        problem_block = f"""
문제 상황: {data["situation"]}
핵심 문제: {data["problem"]}
""".strip()
        guidance = (
            "이 답변은 문제 상황에 대한 해결책 제안입니다. "
            "화자가 문제를 인지했음을 표현하고, 구체적이고 타당한 해결책을 제안했는지, "
            "답변 구성(문제 인지 → 해결책 → 마무리)이 자연스러운지 평가하세요."
        )

    return f"""
{problem_block}

사용자 영어 답변: {data["userAnswer"]}

평가 지침:
{guidance}

평가 기준:
1. 실제 토익 스피킹 채점 기준(내용의 적절성과 완결성, 문법, 어휘, 답변 구성)에 따라 평가하세요.
2. 텍스트 답변이므로 발음, 억양, 유창성은 평가하지 마세요.
3. 정답은 하나가 아니며, 의미가 통하고 적절한 표현이면 다양한 표현을 인정하세요.
4. 모범 답안과 표현이 다르다는 이유만으로 감점하지 마세요.
5. score, contentScore, grammarScore, vocabularyScore는 반드시 0에서 100 사이의 정수(백분율 점수)로 매기세요. 10점 만점이나 5점 만점 척도를 사용하지 마세요. 완벽한 답변은 90점 이상, 사소한 오류가 있는 좋은 답변은 70~89점, 눈에 띄는 오류가 있는 답변은 40~69점, 질문에 제대로 답하지 못한 답변은 0~39점입니다.

응답은 지정된 JSON 스키마와 일치해야 합니다.
""".strip()


def evaluate_with_openai(data):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=25)
    model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    system_message = (
        "당신은 토익 스피킹 답변을 채점하는 평가자입니다. "
        "실제 시험 채점 기준에 따라 공정하고 구체적으로 평가하세요. "
        "JSON 외의 텍스트는 반환하지 마세요."
    )
    prompt = build_prompt(data)

    langfuse = get_langfuse_client()
    generation_cm = None
    if langfuse is not None:
        generation_cm = langfuse.start_as_current_observation(
            as_type="generation",
            name="toeic-speaking-evaluate",
            model=model,
            input={
                "part": data["part"],
                "system": system_message,
                "prompt": prompt,
                "userAnswer": data["userAnswer"],
            },
        )

    generation = generation_cm.__enter__() if generation_cm is not None else None

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "toeic_speaking_evaluation",
                    "schema": EVALUATION_SCHEMA,
                    "strict": True,
                }
            },
            reasoning={"effort": "low"},
            max_output_tokens=1600,
        )

        output_text = getattr(response, "output_text", "")
        if not output_text:
            raise ValueError("Empty model response")

        result = normalize_result(json.loads(output_text), data["userAnswer"])

        if generation is not None:
            usage = getattr(response, "usage", None)
            usage_details = None
            if usage is not None:
                usage_details = {
                    "input": getattr(usage, "input_tokens", None),
                    "output": getattr(usage, "output_tokens", None),
                    "total": getattr(usage, "total_tokens", None),
                }
            generation.update(output=result, usage_details=usage_details)
            generation.score(name="overall_score", value=result["score"] / 100)

        return result
    except Exception as error:
        if generation is not None:
            generation.update(level="ERROR", status_message=str(error))
        raise
    finally:
        if generation_cm is not None:
            generation_cm.__exit__(None, None, None)


def _run_evaluation(raw_body):
    try:
        body_data = json.loads(raw_body or "{}")
    except json.JSONDecodeError:
        return 400, {"error": "요청 형식이 올바르지 않습니다."}

    data, error = validate_body(body_data)
    if error:
        return 400, {"error": error}

    try:
        result = evaluate_with_openai(data)
    except Exception:
        return 500, {"error": "평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."}

    return 200, result


def run_evaluation(raw_body):
    if not is_configured():
        return _run_evaluation(raw_body)

    from langfuse import observe

    traced = observe(name="api-evaluate", as_type="span")(_run_evaluation)
    try:
        return traced(raw_body)
    finally:
        flush_langfuse()
