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

  // --------------------------------------------------------------------
  // ✅ Handle InfoBot queries
  // --------------------------------------------------------------------
  // Use setTimeout to ensure DOM is fully loaded
  setTimeout(() => {
    const infobotQueryInput = document.getElementById("infobot-query");
    const infobotAskBtn = document.getElementById("infobot-ask-btn");
    const infobotAnswer = document.getElementById("infobot-answer");
    const infobotLoading = document.getElementById("infobot-loading");

    if (infobotQueryInput && infobotAskBtn && infobotAnswer && infobotLoading) {
      console.log("InfoBot initialized successfully");

      // Handle Ask button click
      infobotAskBtn.addEventListener("click", async () => {
        console.log("InfoBot Ask button clicked");
        const query = infobotQueryInput.value.trim();
        if (!query) {
          alert("Please enter a question first.");
          return;
        }
        console.log("Query:", query);

        // Show loading, hide answer
        infobotLoading.style.display = "block";
        infobotAnswer.style.display = "none";
        infobotAnswer.innerHTML = "";

        try {
          // Extract topic slug from URL or data attribute
          const topicElement = document.querySelector("[data-topic-slug]");
          const topicSlug = topicElement ? topicElement.dataset.topicSlug : "";

          if (!topicSlug) {
            throw new Error("Topic slug not found");
          }

          // Make AJAX request to InfoBot endpoint
          const response = await fetch(`/interactive/info-bot/${topicSlug}/?query=${encodeURIComponent(query)}`, {
            method: "GET",
            headers: {
              "X-Requested-With": "XMLHttpRequest"
            }
          });

          const data = await response.json();

          // Hide loading, show answer
          infobotLoading.style.display = "none";

          if (data.answer) {
            infobotAnswer.innerHTML = data.answer;
            infobotAnswer.style.display = "block";

            // Scroll to answer
            infobotAnswer.scrollIntoView({ behavior: "smooth", block: "nearest" });
          } else {
            infobotAnswer.innerHTML = "<div style='color:red;'>Sorry, I couldn't find an answer to that question.</div>";
            infobotAnswer.style.display = "block";
          }

        } catch (error) {
          console.error("InfoBot error:", error);
          infobotLoading.style.display = "none";
          infobotAnswer.innerHTML = "<div style='color:red;'>Error: Unable to get an answer. Please try again.</div>";
          infobotAnswer.style.display = "block";
        }
      });

      // Allow Enter key to submit query
      infobotQueryInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          infobotAskBtn.click();
        }
      });
    } else {
      console.error("InfoBot elements not found:", {
        infobotQueryInput,
        infobotAskBtn,
        infobotAnswer,
        infobotLoading
      });
    }
  }, 100); // Wait 100ms for DOM to be fully ready
});
