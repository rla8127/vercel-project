const state = {
  part: "",
  isGenerating: false,
  currentQuestion: null
};

const partInputs = document.querySelectorAll("input[name='part']");
const generateButton = document.querySelector("#generate-button");
const generateMessage = document.querySelector("#generate-message");
const questionEmpty = document.querySelector("#question-empty");
const questionArea = document.querySelector("#question-area");

const part3Template = document.querySelector("#part3-template");
const part3ItemTemplate = document.querySelector("#part3-item-template");
const part5Template = document.querySelector("#part5-template");
const resultTemplate = document.querySelector("#result-template");

function escapeText(value) {
  return String(value ?? "");
}

function scoreText(value) {
  const score = Number.isFinite(Number(value)) ? Math.round(Number(value)) : 0;
  return `${Math.max(0, Math.min(100, score))}점`;
}

function hasKorean(text) {
  return /[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(text);
}

function hasEnglish(text) {
  return /[A-Za-z]/.test(text);
}

function validateAnswer(answer) {
  if (!answer) {
    return "답변을 입력해 주세요.";
  }
  if (hasKorean(answer) && !hasEnglish(answer)) {
    return "영어로 답변을 작성해 주세요.";
  }
  return "";
}

function setGenerateMessage(text, type = "error") {
  generateMessage.textContent = text;
  generateMessage.classList.toggle("info", type === "info");
}

function setGenerating(isGenerating) {
  state.isGenerating = isGenerating;
  generateButton.disabled = isGenerating || !state.part;
  generateButton.textContent = isGenerating ? "문제 만드는 중..." : "문제 만들기";
}

function buildResultBlock(container, result) {
  container.innerHTML = "";
  const fragment = resultTemplate.content.cloneNode(true);

  fragment.querySelector(".score-total").textContent = scoreText(result.score);
  fragment.querySelector(".score-content").textContent = scoreText(result.contentScore);
  fragment.querySelector(".score-grammar").textContent = scoreText(result.grammarScore);
  fragment.querySelector(".score-vocabulary").textContent = scoreText(result.vocabularyScore);
  fragment.querySelector(".sample-answer").textContent = escapeText(result.sampleAnswer);
  fragment.querySelector(".feedback-text").textContent = escapeText(result.feedback);

  const list = fragment.querySelector(".improvement-list");
  const improvements = Array.isArray(result.improvements) ? result.improvements : [];

  if (improvements.length === 0) {
    const item = document.createElement("li");
    item.innerHTML = "<strong>개선할 부분이 없습니다.</strong><p>답변이 이미 적절하다면 그대로 사용해도 좋습니다.</p>";
    list.appendChild(item);
  } else {
    improvements.forEach((improvement) => {
      const item = document.createElement("li");
      const title = document.createElement("strong");
      const reason = document.createElement("p");
      title.textContent = `${escapeText(improvement.original)} → ${escapeText(improvement.suggestion)}`;
      reason.textContent = escapeText(improvement.reason);
      item.append(title, reason);
      list.appendChild(item);
    });
  }

  container.appendChild(fragment);
  container.classList.remove("hidden");
}

async function requestEvaluation(payload) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || "평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
    }

    return { ok: true, result: data };
  } catch (error) {
    const isAbort = error.name === "AbortError";
    const message = isAbort
      ? "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."
      : error.message || "평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
    return { ok: false, message };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function wireEvalCard(card, buildPayload) {
  const textarea = card.querySelector(".answer-input");
  const button = card.querySelector(".eval-button");
  const message = card.querySelector(".item-message");
  const resultContainer = card.querySelector(".result-container");

  let isSubmitting = false;

  button.addEventListener("click", async () => {
    if (isSubmitting) {
      return;
    }

    const answer = textarea.value.trim();
    const validationMessage = validateAnswer(answer);
    if (validationMessage) {
      message.textContent = validationMessage;
      message.classList.remove("info");
      return;
    }

    isSubmitting = true;
    button.disabled = true;
    button.textContent = "평가 중...";
    message.textContent = "답변을 평가하고 있습니다.";
    message.classList.add("info");

    const payload = buildPayload(answer);
    const outcome = await requestEvaluation(payload);

    if (outcome.ok) {
      message.textContent = "";
      message.classList.remove("info");
      buildResultBlock(resultContainer, outcome.result);
    } else {
      message.textContent = outcome.message;
      message.classList.remove("info");
    }

    isSubmitting = false;
    button.disabled = false;
    button.textContent = card.dataset.evalLabel || "평가받기";
  });
}

function renderPart3(question) {
  questionArea.innerHTML = "";
  const fragment = part3Template.content.cloneNode(true);

  fragment.querySelector(".context-text").textContent = question.context;
  fragment.querySelector(".dialogue-text").textContent = question.dialogue;

  const list = fragment.querySelector(".question-list");

  question.questions.forEach((questionText, index) => {
    const itemFragment = part3ItemTemplate.content.cloneNode(true);
    const card = itemFragment.querySelector(".question-card");
    card.dataset.evalLabel = "이 문항 평가받기";

    itemFragment.querySelector(".question-number").textContent = String(index + 1);
    itemFragment.querySelector(".question-text").textContent = questionText;

    wireEvalCard(card, (answer) => ({
      part: "part3",
      context: question.context,
      dialogue: question.dialogue,
      question: questionText,
      userAnswer: answer
    }));

    list.appendChild(itemFragment);
  });

  questionArea.appendChild(fragment);
}

function renderPart5(question) {
  questionArea.innerHTML = "";
  const fragment = part5Template.content.cloneNode(true);

  fragment.querySelector(".situation-text").textContent = question.situation;

  const card = fragment.querySelector(".question-card");
  card.dataset.evalLabel = "평가받기";

  wireEvalCard(card, (answer) => ({
    part: "part5",
    situation: question.situation,
    problem: question.problem,
    userAnswer: answer
  }));

  questionArea.appendChild(fragment);
}

async function generateQuestion() {
  if (state.isGenerating || !state.part) {
    return;
  }

  setGenerating(true);
  setGenerateMessage("문제를 만들고 있습니다.", "info");

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ part: state.part }),
      signal: controller.signal
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || "문제를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    }

    state.currentQuestion = data;
    questionEmpty.classList.add("hidden");
    questionArea.classList.remove("hidden");

    if (data.part === "part3") {
      renderPart3(data);
    } else {
      renderPart5(data);
    }

    setGenerateMessage("");
  } catch (error) {
    const isAbort = error.name === "AbortError";
    setGenerateMessage(
      isAbort
        ? "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."
        : error.message || "문제를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
    );
  } finally {
    window.clearTimeout(timeoutId);
    setGenerating(false);
  }
}

partInputs.forEach((input) => {
  input.addEventListener("change", () => {
    state.part = input.value;
    generateButton.disabled = state.isGenerating || !state.part;
    setGenerateMessage("");
  });
});

generateButton.addEventListener("click", generateQuestion);

const themeToggle = document.querySelector("#theme-toggle");
const themeToggleIcon = themeToggle?.querySelector(".theme-toggle-icon");

function applyThemeIcon(theme) {
  if (themeToggleIcon) {
    themeToggleIcon.textContent = theme === "dark" ? "☀️" : "🌙";
  }
}

applyThemeIcon(document.documentElement.getAttribute("data-theme"));

themeToggle?.addEventListener("click", () => {
  const nextTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", nextTheme);
  localStorage.setItem("theme", nextTheme);
  applyThemeIcon(nextTheme);
});
