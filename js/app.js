const fallbackExercises = [
  {
    id: 1,
    level: "beginner",
    sentence: "나는 매일 아침 커피를 마신다.",
    exampleAnswer: "I drink coffee every morning."
  },
  {
    id: 2,
    level: "beginner",
    sentence: "그녀는 어제 영화를 보았다.",
    exampleAnswer: "She watched a movie yesterday."
  },
  {
    id: 3,
    level: "beginner",
    sentence: "우리는 학교에 걸어간다.",
    exampleAnswer: "We walk to school."
  },
  {
    id: 4,
    level: "intermediate",
    sentence: "나는 시간을 절약할 수 있기 때문에 온라인 쇼핑을 선호한다.",
    exampleAnswer: "I prefer shopping online because it saves me time."
  },
  {
    id: 5,
    level: "intermediate",
    sentence: "비가 많이 와서 우리는 약속을 취소해야 했다.",
    exampleAnswer: "Because it rained heavily, we had to cancel our appointment."
  },
  {
    id: 6,
    level: "intermediate",
    sentence: "나는 새로운 언어를 배우는 것이 자신감을 높여 준다고 생각한다.",
    exampleAnswer: "I think learning a new language increases confidence."
  }
];

const state = {
  exercises: fallbackExercises,
  level: "",
  currentExercise: null,
  currentIndexByLevel: {
    beginner: 0,
    intermediate: 0
  },
  isSubmitting: false
};

const form = document.querySelector("#practice-form");
const levelInputs = document.querySelectorAll("input[name='level']");
const koreanSentence = document.querySelector("#korean-sentence");
const answerInput = document.querySelector("#user-answer");
const formMessage = document.querySelector("#form-message");
const submitButton = document.querySelector("#submit-button");
const nextButton = document.querySelector("#next-button");
const resultEmpty = document.querySelector("#result-empty");
const resultContent = document.querySelector("#result-content");

async function loadExercises() {
  try {
    const response = await fetch("data/exercises.json", { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (Array.isArray(data) && data.length > 0) {
      state.exercises = data;
    }
  } catch (error) {
    console.info("정적 문제 파일을 불러오지 못해 내장 문제를 사용합니다.", error);
  }
}

function getExercisesByLevel(level) {
  return state.exercises.filter((exercise) => exercise.level === level);
}

function setMessage(text, type = "error") {
  formMessage.textContent = text;
  formMessage.classList.toggle("info", type === "info");
}

function clearMessage() {
  setMessage("");
}

function setCurrentExercise(level, direction = "current") {
  const list = getExercisesByLevel(level);
  if (list.length === 0) {
    state.currentExercise = null;
    koreanSentence.textContent = "이 난이도의 문제가 아직 없습니다.";
    return;
  }

  if (direction === "next") {
    state.currentIndexByLevel[level] = (state.currentIndexByLevel[level] + 1) % list.length;
  }

  const index = state.currentIndexByLevel[level] % list.length;
  state.currentExercise = list[index];
  koreanSentence.textContent = state.currentExercise.sentence;
}

function resetResult() {
  resultEmpty.classList.remove("hidden");
  resultContent.classList.add("hidden");
}

function validateInput() {
  const answer = answerInput.value.trim();
  const hasKorean = /[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(answer);
  const hasEnglish = /[A-Za-z]/.test(answer);

  if (!state.level) {
    return "난이도를 선택해 주세요.";
  }

  if (!answer) {
    return "영어 문장을 입력해 주세요.";
  }

  if (hasKorean && !hasEnglish) {
    return "영어로 답변을 작성해 주세요.";
  }

  if (!state.currentExercise) {
    return "문제를 불러온 뒤 다시 시도해 주세요.";
  }

  return "";
}

function escapeText(value) {
  return String(value ?? "");
}

function scoreText(value) {
  const score = Number.isFinite(Number(value)) ? Math.round(Number(value)) : 0;
  return `${Math.max(0, Math.min(100, score))}점`;
}

function renderResult(result) {
  document.querySelector("#score-total").textContent = scoreText(result.score);
  document.querySelector("#score-meaning").textContent = scoreText(result.meaningScore);
  document.querySelector("#score-grammar").textContent = scoreText(result.grammarScore);
  document.querySelector("#score-naturalness").textContent = scoreText(result.naturalnessScore);
  document.querySelector("#corrected-sentence").textContent = escapeText(result.correctedSentence);
  document.querySelector("#feedback-text").textContent = escapeText(result.feedback);

  const mistakeList = document.querySelector("#mistake-list");
  mistakeList.innerHTML = "";

  const mistakes = Array.isArray(result.mistakes) ? result.mistakes : [];
  if (mistakes.length === 0) {
    const item = document.createElement("li");
    item.innerHTML = "<strong>수정할 부분이 없습니다.</strong><p>문장이 이미 자연스럽다면 그대로 사용해도 좋습니다.</p>";
    mistakeList.appendChild(item);
  } else {
    mistakes.forEach((mistake) => {
      const item = document.createElement("li");
      const title = document.createElement("strong");
      const reason = document.createElement("p");
      title.textContent = `${escapeText(mistake.original)} → ${escapeText(mistake.correction)}`;
      reason.textContent = escapeText(mistake.reason);
      item.append(title, reason);
      mistakeList.appendChild(item);
    });
  }

  resultEmpty.classList.add("hidden");
  resultContent.classList.remove("hidden");
}

function setSubmitting(isSubmitting) {
  state.isSubmitting = isSubmitting;
  submitButton.disabled = isSubmitting;
  submitButton.textContent = isSubmitting ? "평가 중..." : "AI 평가 받기";
}

async function submitEvaluation(event) {
  event.preventDefault();

  if (state.isSubmitting) {
    return;
  }

  const validationMessage = validateInput();
  if (validationMessage) {
    setMessage(validationMessage);
    return;
  }

  clearMessage();
  setSubmitting(true);
  setMessage("답변을 평가하고 있습니다.", "info");

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch("/api", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        level: state.level,
        koreanSentence: state.currentExercise.sentence,
        userAnswer: answerInput.value.trim()
      }),
      signal: controller.signal
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(payload.error || "평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
    }

    renderResult(payload);
    clearMessage();
  } catch (error) {
    const isAbort = error.name === "AbortError";
    setMessage(isAbort ? "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요." : "평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
  } finally {
    window.clearTimeout(timeoutId);
    setSubmitting(false);
  }
}

levelInputs.forEach((input) => {
  input.addEventListener("change", () => {
    state.level = input.value;
    setCurrentExercise(state.level);
    answerInput.value = "";
    clearMessage();
    resetResult();
  });
});

nextButton.addEventListener("click", () => {
  if (!state.level) {
    setMessage("난이도를 선택해 주세요.");
    return;
  }
  setCurrentExercise(state.level, "next");
  answerInput.value = "";
  clearMessage();
  resetResult();
});

form.addEventListener("submit", submitEvaluation);

loadExercises();
