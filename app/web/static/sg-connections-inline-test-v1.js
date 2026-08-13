(() => {
  const form = document.getElementById("xps2-form");
  if (!(form instanceof HTMLFormElement)) return;

  const testButton = form.querySelector('button[type="submit"][name="action"][value="test"]');
  const actions = form.querySelector(".xps2-actions");
  if (!(testButton instanceof HTMLButtonElement) || !actions) return;

  const result = document.createElement("div");
  result.className = "xps2-inline-test-result";
  result.setAttribute("role", "status");
  result.setAttribute("aria-live", "polite");
  result.hidden = true;
  result.style.marginTop = "14px";
  result.style.padding = "12px 16px";
  result.style.borderRadius = "10px";
  result.style.border = "1px solid var(--sg-line, #31455c)";
  result.style.background = "var(--sg-field, #0d1825)";
  result.style.fontWeight = "700";
  result.style.lineHeight = "1.45";
  actions.appendChild(result);

  const showResult = (message, ok) => {
    result.hidden = false;
    result.textContent = message;
    result.dataset.tone = ok ? "success" : "error";
    result.style.borderColor = ok ? "rgba(85, 213, 146, .55)" : "rgba(239, 123, 137, .65)";
    result.style.color = ok ? "var(--sg-green, #55d592)" : "var(--sg-red, #ef7b89)";
  };

  let running = false;
  form.addEventListener("submit", async (event) => {
    const submitter = event.submitter;
    if (!(submitter instanceof HTMLButtonElement) || submitter !== testButton) return;

    event.preventDefault();
    if (running) return;
    running = true;

    const originalText = testButton.textContent;
    testButton.disabled = true;
    testButton.textContent = "Проверяю…";
    showResult("Проверяется полный Xray candidate. Изменения пока не применяются…", true);

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: {"X-Requested-With": "XMLHttpRequest"},
        redirect: "follow",
      });

      const html = await response.text();
      const documentCopy = new DOMParser().parseFromString(html, "text/html");
      const messages = [...documentCopy.querySelectorAll(".flash-stack .flash-message")];
      const message = messages.map(item => item.textContent.trim()).filter(Boolean).join(" ");
      const failed = !response.ok || messages.some(item => item.classList.contains("error"));

      if (response.url.includes("/login")) {
        showResult("Сессия панели завершилась. Войдите снова и повторите проверку.", false);
      } else if (message) {
        showResult(message, !failed);
      } else if (response.ok) {
        showResult("Проверка завершилась, но сервер не вернул текст результата.", false);
      } else {
        showResult(`Проверка не выполнена: HTTP ${response.status}.`, false);
      }
    } catch (error) {
      showResult(`Проверка не выполнена: ${error?.message || "ошибка запроса"}.`, false);
    } finally {
      running = false;
      testButton.disabled = false;
      testButton.textContent = originalText;
    }
  });
})();
