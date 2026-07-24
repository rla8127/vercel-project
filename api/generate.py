import json
import os
import random

from observability import flush_langfuse, get_langfuse_client, is_configured


ALLOWED_PARTS = {"part3", "part5"}

PART3_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["context", "dialogue", "questions"],
    "properties": {
        "context": {"type": "string"},
        "dialogue": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
    },
}

PART5_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["situation", "problem"],
    "properties": {
        "situation": {"type": "string"},
        "problem": {"type": "string"},
    },
}

TOPIC_HINTS = [
    "친구와의 약속",
    "식당 예약",
    "여행 일정",
    "사내 회의",
    "쇼핑과 배송",
    "동호회 모임",
    "이사와 집 수리",
    "헬스장 또는 강좌 등록",
    "병원 예약",
    "행사 초대와 참석",
]


def normalize_part3(payload):
    context = str(payload.get("context") or "").strip()
    dialogue = str(payload.get("dialogue") or "").strip()
    questions_raw = payload.get("questions")

    questions = []
    if isinstance(questions_raw, list):
        for question in questions_raw:
            text = str(question or "").strip()
            if text:
                questions.append(text)

    return {
        "part": "part3",
        "context": context,
        "dialogue": dialogue,
        "questions": questions[:3],
    }


def normalize_part5(payload):
    return {
        "part": "part5",
        "situation": str(payload.get("situation") or "").strip(),
        "problem": str(payload.get("problem") or "").strip(),
    }


def build_prompt_part3(topic):
    return f"""
토익 스피킹 Part 3(대화문 기반 질의응답) 문제를 새로 만드세요.

주제 힌트: {topic}

요구사항:
1. 일상적인 상황을 한국어로 한 문장 설명하세요 (context).
2. 그 상황에 맞는 짧은 영어 대화문 또는 안내 메시지를 작성하세요 (dialogue). 3~5문장 길이로 작성하세요.
3. 그 대화문 내용을 바탕으로 한 영어 질문 3개를 작성하세요 (questions).
   - 첫 번째 질문은 대화문에 명시된 구체적 정보(시간, 장소, 이름 등)를 묻는 질문으로 만드세요.
   - 두 번째 질문은 대화문에 명시된 다른 구체적 정보를 묻는 질문으로 만드세요.
   - 세 번째 질문은 대화문 내용을 바탕으로 추론하거나 의견을 묻는 질문으로 만드세요.
4. 매번 새로운 인물, 장소, 세부 상황을 사용해 이전과 다른 문제를 만드세요.
5. context는 한국어로, dialogue와 questions는 영어로 작성하세요.

응답은 지정된 JSON 스키마와 정확히 일치해야 합니다.
""".strip()


def build_prompt_part5(topic):
    return f"""
토익 스피킹 Part 5(문제 해결하기, Propose a Solution) 문제를 새로 만드세요.

주제 힌트: {topic}

요구사항:
1. 전화 음성 메시지 형태로, 화자가 겪고 있는 일상적인 문제 상황을 설명하는 텍스트를 작성하세요 (situation). 4~6문장 길이로, 문제 상황과 배경, 요청 사항이 드러나야 합니다. 한국어로 작성하세요.
2. situation에서 화자가 겪는 핵심 문제를 한 문장으로 요약하세요 (problem). 한국어로 작성하세요.
3. 매번 새로운 인물, 장소, 세부 문제를 사용해 이전과 다른 문제를 만드세요.
4. 문제는 사용자가 "문제를 인지했다는 표현 → 해결책 제안 → 마무리" 구조로 영어 답변을 만들 수 있을 정도로 구체적이어야 합니다.

응답은 지정된 JSON 스키마와 정확히 일치해야 합니다.
""".strip()


def generate_with_openai(part):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=25)
    model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    topic = random.choice(TOPIC_HINTS)

    if part == "part3":
        prompt = build_prompt_part3(topic)
        schema = PART3_SCHEMA
        schema_name = "toeic_speaking_part3_question"
    else:
        prompt = build_prompt_part5(topic)
        schema = PART5_SCHEMA
        schema_name = "toeic_speaking_part5_question"

    system_message = (
        "당신은 토익 스피킹 문제 출제자입니다. "
        "실제 시험과 유사한 자연스러운 상황을 만들고, "
        "매번 다양한 소재를 사용하세요. "
        "JSON 외의 텍스트는 반환하지 마세요."
    )

    langfuse = get_langfuse_client()
    generation_cm = None
    if langfuse is not None:
        generation_cm = langfuse.start_as_current_observation(
            as_type="generation",
            name="toeic-speaking-generate",
            model=model,
            input={
                "part": part,
                "topic": topic,
                "system": system_message,
                "prompt": prompt,
            },
            metadata={"schema_name": schema_name},
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
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
            reasoning={"effort": "low"},
            max_output_tokens=1600,
        )

        output_text = getattr(response, "output_text", "")
        if not output_text:
            raise ValueError("Empty model response")

        payload = json.loads(output_text)

        if part == "part3":
            result = normalize_part3(payload)
            if not result["context"] or not result["dialogue"] or len(result["questions"]) != 3:
                raise ValueError("Incomplete part3 generation result")
        else:
            result = normalize_part5(payload)
            if not result["situation"] or not result["problem"]:
                raise ValueError("Incomplete part5 generation result")

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

        return result
    except Exception as error:
        if generation is not None:
            generation.update(level="ERROR", status_message=str(error))
        raise
    finally:
        if generation_cm is not None:
            generation_cm.__exit__(None, None, None)


def _run_generation(raw_body):
    try:
        body_data = json.loads(raw_body or "{}")
    except json.JSONDecodeError:
        return 400, {"error": "요청 형식이 올바르지 않습니다."}

    part = str(body_data.get("part", "")).strip()
    if not part:
        return 400, {"error": "문제 유형을 선택해 주세요."}
    if part not in ALLOWED_PARTS:
        return 400, {"error": "지원하지 않는 문제 유형입니다."}

    try:
        result = generate_with_openai(part)
    except Exception:
        return 500, {"error": "문제를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."}

    return 200, result


def run_generation(raw_body):
    if not is_configured():
        return _run_generation(raw_body)

    from langfuse import observe

    traced = observe(name="api-generate", as_type="span")(_run_generation)
    try:
        return traced(raw_body)
    finally:
        flush_langfuse()
