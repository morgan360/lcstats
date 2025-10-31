document.addEventListener("DOMContentLoaded", () => {
  // --- CSRF and setup ---
  const csrfTokenInput = document.querySelector("[name=csrfmiddlewaretoken]");
  const csrfToken = csrfTokenInput ? csrfTokenInput.value : "";
  const totalParts = document.querySelectorAll(".check-btn").length;
  let completedParts = 0;

  // --- Initialize MathLive fields ---
  document.querySelectorAll("math-field").forEach(mf => {
    mf.smartMode = false;
    mf.inlineShortcuts = {};
    mf.mathVirtualKeyboardPolicy = "manual";
    mf.keypressSound = null;
    mf.plonkSound = null;
  });

  // --- Handle "Check Answer" buttons ---
  document.querySelectorAll(".check-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const partId = btn.dataset.part;
      const mf = document.getElementById("mf-" + partId);
      const feedbackBox = document.getElementById("feedback-" + partId);

      if (!mf) return;

      const answer = mf.getValue("latex");

      // Require an answer
      if (!answer.trim()) {
        feedbackBox.innerHTML = "<div style='color:red;'>Please enter an answer first.</div>";
        feedbackBox.style.display = "block";
        return;
      }

      // Show checking message
      feedbackBox.innerHTML = "Checking...";
      feedbackBox.style.display = "block";

      // Build POST data
      const formData = new FormData();
      formData.append("csrfmiddlewaretoken", csrfToken);
      formData.append("part_id", partId);
      formData.append("answer_" + partId, answer);

      try {
        // --- Send to Django view ---
        const res = await fetch(window.location.href, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        // --- Parse JSON response ---
        const data = await res.json();

        if (data.feedback) {
          const color = data.is_correct ? "green" : "red";
          feedbackBox.innerHTML = `<div style="color:${color};">${data.feedback} (Score: ${data.score}/100)</div>`;
        } else {
          feedbackBox.innerHTML = "<div style='color:red;'>Error checking answer.</div>";
        }

        // Mark this part as completed
        if (!feedbackBox.classList.contains("done")) {
          feedbackBox.classList.add("done");
          completedParts++;
        }

        // Reveal "Next" button if all parts done
        if (completedParts >= totalParts) {
          const nextWrapper = document.getElementById("next-btn-wrapper");
          if (nextWrapper) nextWrapper.style.display = "block";
        }

      } catch (e) {
        console.error("AJAX error:", e);
        feedbackBox.innerHTML = "<div style='color:red;'>Error checking answer.</div>";
      }
    });
  });

  // --------------------------------------------------------------------
  // ✅ Handle "Show Full Solution" toggle
  // --------------------------------------------------------------------
  const solBtn = document.getElementById("show-solution-btn");
  const solContent = document.getElementById("solution-content");

  if (solBtn && solContent) {
    solBtn.addEventListener("click", () => {
      const visible = solContent.style.display === "block";
      solContent.style.display = visible ? "none" : "block";
      solBtn.textContent = visible ? "Show Full Solution" : "Hide Solution";

      // Optional: smooth scroll into view when opening
      if (!visible) {
        solContent.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }
});
