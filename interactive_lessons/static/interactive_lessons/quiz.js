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
    // "auto": virtual keyboard appears on focus for touch devices only;
    // desktop users keep typing on their physical keyboard
    mf.mathVirtualKeyboardPolicy = "auto";
    mf.keypressSound = null;
    mf.plonkSound = null;
  });

  // --- Handle "Check Answer" buttons ---
  document.querySelectorAll(".check-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const partId = btn.dataset.part;
      const feedbackBox = document.getElementById("feedback-" + partId);

      // Check for text input (physics/text questions) or math field (math questions)
      const textInput = document.getElementById("answer-" + partId);
      const mathField = document.getElementById("mf-" + partId);

      let answer = "";
      if (textInput) {
        answer = textInput.value;
      } else if (mathField) {
        answer = mathField.getValue("latex");
      } else {
        return; // No input field found
      }

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
          if (data.is_correct) {
            // Correct answer - show success message
            feedbackBox.innerHTML = `
              <div class="rounded-md bg-green-50 border border-green-300 px-4 py-3 mt-2">
                <div class="flex items-start">
                  <span class="text-2xl mr-2">✅</span>
                  <div class="flex-1">
                    <div class="font-semibold text-green-800">Correct!</div>
                    <div class="text-sm text-green-700 mt-1">${data.feedback}</div>
                    <div class="text-xs text-green-600 mt-1">Score: ${data.score}/100</div>
                  </div>
                </div>
              </div>
            `;
          } else {
            // Incorrect answer - show detailed feedback
            const hintText = data.hint || "";
            feedbackBox.innerHTML = `
              <div class="rounded-md bg-red-50 border border-red-300 px-4 py-3 mt-2">
                <div class="flex items-start">
                  <span class="text-2xl mr-2">❌</span>
                  <div class="flex-1">
                    <div class="font-semibold text-red-800">Not quite right</div>
                    <div class="text-sm text-red-700 mt-2 leading-relaxed">${data.feedback}</div>
                    ${hintText ? `
                      <div class="mt-3 rounded bg-amber-50 border-l-4 border-amber-400 px-3 py-2">
                        <div class="flex items-start">
                          <span class="mr-2">💡</span>
                          <div>
                            <div class="font-semibold text-amber-800 text-xs">Next step:</div>
                            <div class="text-sm text-amber-700 mt-1">${hintText}</div>
                          </div>
                        </div>
                      </div>
                    ` : ''}
                    <div class="text-xs text-red-600 mt-2">Score: ${data.score}/100</div>
                  </div>
                </div>
              </div>
            `;
          }

          // Re-render KaTeX in dynamically inserted feedback
          if (window.renderMathInElement) {
            renderMathInElement(feedbackBox, {
              delimiters: [
                {left: "$$", right: "$$", display: true},
                {left: "\\[", right: "\\]", display: true},
                {left: "\\(", right: "\\)", display: false},
                {left: "$", right: "$", display: false}
              ],
              throwOnError: false
            });
          }

          // Store attempt ID and show feedback buttons
          if (data.attempt_id) {
            // Store attempt ID in a data attribute
            feedbackBox.dataset.attemptId = data.attempt_id;

            // Show feedback buttons
            const questionFeedbackDiv = document.getElementById(`question-feedback-${partId}`);
            if (questionFeedbackDiv) {
              questionFeedbackDiv.classList.remove('hidden');
              // Reset feedback message
              const feedbackMessage = document.getElementById(`question-feedback-message-${partId}`);
              if (feedbackMessage) {
                feedbackMessage.style.display = 'none';
              }
              // Show buttons again
              questionFeedbackDiv.querySelectorAll('button').forEach(btn => btn.style.display = 'inline-flex');
            }
          }

          // Update attempt count display
          if (data.attempt_count !== undefined) {
            const attemptCountSpan = document.getElementById(`attempt-count-${partId}`);
            const attemptPluralSpan = document.getElementById(`attempt-plural-${partId}`);
            if (attemptCountSpan) {
              attemptCountSpan.textContent = data.attempt_count;
            }
            if (attemptPluralSpan) {
              // Update plural suffix (empty string for 1, 's' for others)
              attemptPluralSpan.textContent = data.attempt_count === 1 ? '' : 's';
            }
          }

          // Handle solution unlock
          if (data.solution_unlocked !== undefined && data.solution_unlocked) {
            // Fetch and display the solution via AJAX instead of reloading
            fetchAndDisplaySolution(partId);
          }
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

// ============================================================================
// Question Feedback Submission (global function for onclick handlers)
// ============================================================================
function submitQuestionFeedback(partId, feedbackType) {
  console.log('submitQuestionFeedback called:', { partId, feedbackType });

  // Get the attempt ID from the feedback box data attribute
  const feedbackBox = document.getElementById(`feedback-${partId}`);
  if (!feedbackBox || !feedbackBox.dataset.attemptId) {
    console.error('No attempt ID found for part', partId);
    alert('Unable to submit feedback. Please try answering the question first.');
    return;
  }

  const attemptId = feedbackBox.dataset.attemptId;
  console.log('Attempt ID:', attemptId);

  // Disable buttons immediately
  const questionFeedbackDiv = document.getElementById(`question-feedback-${partId}`);
  const buttons = questionFeedbackDiv.querySelectorAll('button');
  buttons.forEach(btn => btn.disabled = true);

  // Helper to get CSRF token from cookie
  function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Send feedback to server
  fetch(`/students/question-attempt/${attemptId}/feedback/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      feedback_type: feedbackType
    })
  })
  .then(response => response.json())
  .then(data => {
    console.log('Feedback response:', data);
    if (data.success) {
      // Hide buttons
      buttons.forEach(btn => btn.style.display = 'none');
      // Show thank you message
      const feedbackMessage = document.getElementById(`question-feedback-message-${partId}`);
      if (feedbackMessage) {
        feedbackMessage.style.display = 'inline';
      }
    } else {
      console.error('Feedback submission failed:', data);
      // Re-enable buttons
      buttons.forEach(btn => btn.disabled = false);
      alert('Failed to submit feedback: ' + (data.error || 'Unknown error'));
    }
  })
  .catch(error => {
    console.error('Feedback submission error:', error);
    // Re-enable buttons
    buttons.forEach(btn => btn.disabled = false);
    alert('An error occurred while submitting feedback.');
  });
}

// ============================================================================
// Fetch and Display Solution via AJAX (avoids page reload)
// ============================================================================
async function fetchAndDisplaySolution(partId) {
  try {
    const response = await fetch(`/interactive/get-solution/${partId}/`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    const data = await response.json();

    if (data.success && data.solution_html) {
      // Replace the locked solution box with the actual solution
      const lockedBox = document.getElementById(`solution-locked-${partId}`);
      if (lockedBox) {
        // Create a new solution details element
        const solutionContainer = document.createElement('details');
        solutionContainer.className = 'mt-4 rounded-md border border-[#a5d6a7] bg-[#e8f5e9] px-4 py-3 text-lg leading-relaxed';
        solutionContainer.innerHTML = data.solution_html;

        // Replace locked box with solution
        lockedBox.parentElement.replaceChild(solutionContainer, lockedBox);

        // Render KaTeX math in the solution
        if (window.renderMathInElement) {
          renderMathInElement(solutionContainer, {
            delimiters: [
              {left: "$$", right: "$$", display: true},
              {left: "\\[", right: "\\]", display: true},
              {left: "\\(", right: "\\)", display: false},
              {left: "$", right: "$", display: false}
            ],
            throwOnError: false
          });
        }
      }
    } else {
      console.error('Failed to fetch solution:', data.error || 'Unknown error');
    }
  } catch (error) {
    console.error('Error fetching solution:', error);
  }
}
