/* Photograph-your-working, laptop side.
 *
 * The student is at a computer with their copy on the desk and the camera in
 * their pocket. This shows a QR, the phone uploads through it, and this polls
 * until the commentary comes back.
 *
 * Driven entirely by markup: any element with [data-work-capture] and
 * data-part-type / data-part-id is wired on load, so adding this to another
 * question surface is a template change and nothing else.
 */
(function () {
  "use strict";

  var POLL_MS = 2000;
  // Past this the student has wandered off. Stop polling rather than hammer
  // the server from an abandoned tab all afternoon.
  var POLL_LIMIT_MS = 10 * 60 * 1000;

  function csrf(root) {
    var field = document.querySelector("[name=csrfmiddlewaretoken]");
    if (field) return field.value;
    return root.getAttribute("data-csrf") || "";
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  function render(data) {
    var html = "";

    if (!data.readable || data.confidence === "low") {
      html +=
        '<div class="work-warn">Some of that was hard to read, so treat this ' +
        "as a rough steer. A straight-on photo of a flat page in good light " +
        "reads best.</div>";
    }

    if (data.transcription) {
      html +=
        "<details class=\"work-transcript\"><summary>What I read from your page</summary>" +
        '<pre>' + esc(data.transcription) + "</pre></details>";
    }

    if (data.method_feedback) {
      html += "<h4>Your method</h4><p>" + esc(data.method_feedback) + "</p>";
    }

    if (data.steps && data.steps.length) {
      html += '<ul class="work-steps">';
      data.steps.forEach(function (s) {
        var v = s.verdict || "unclear";
        var mark = { correct: "✓", slip: "~", wrong: "✗" }[v] || "?";
        html +=
          '<li><span class="work-v work-v-' + esc(v) + '">' + mark + "</span> " +
          esc(s.step) +
          (s.comment ? "<br><small>" + esc(s.comment) + "</small>" : "") +
          "</li>";
      });
      html += "</ul>";
    }

    if (data.has_diagram && data.diagram_feedback) {
      html += "<h4>Your graph</h4><p>" + esc(data.diagram_feedback) + "</p>";
    }

    if (data.next_step) {
      html += '<h4>Next step</h4><p class="work-next">' + esc(data.next_step) + "</p>";
    }

    // The student's own way out. The photo is of their handwriting and it is
    // kept on the server, so they should not have to wait for the 90-day purge
    // to be rid of it.
    html +=
      '<p class="work-delete"><button type="button" data-action="delete">' +
      "Delete this photo</button></p>";

    return html;
  }

  function wire(root) {
    var partType = root.getAttribute("data-part-type");
    var partId = root.getAttribute("data-part-id");
    var openBtn = root.querySelector("[data-action=open]");
    var panel = root.querySelector("[data-role=panel]");
    var qrImg = root.querySelector("[data-role=qr]");
    var linkEl = root.querySelector("[data-role=link]");
    var statusEl = root.querySelector("[data-role=status]");
    var feedbackEl = root.querySelector("[data-role=feedback]");
    var cancelBtn = root.querySelector("[data-action=cancel]");

    var timer = null;
    var startedAt = 0;
    var submissionId = null;

    function stopPolling() {
      if (timer) window.clearTimeout(timer);
      timer = null;
    }

    function say(text) {
      statusEl.textContent = text;
    }

    function finish(data) {
      stopPolling();
      panel.hidden = true;
      feedbackEl.innerHTML = render(data);
      feedbackEl.hidden = false;
      // The base template's KaTeX pass has already run by now, so anything
      // injected here has to be rendered explicitly.
      if (window.renderMathInElement) {
        try {
          window.renderMathInElement(feedbackEl, {
            delimiters: [
              { left: "$$", right: "$$", display: true },
              { left: "$", right: "$", display: false }
            ],
            throwOnError: false
          });
        } catch (e) {
          /* feedback still readable as plain text */
        }
      }
      var deleteBtn = feedbackEl.querySelector("[data-action=delete]");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", function () { removePhoto(deleteBtn); });
      }

      openBtn.disabled = false;
      openBtn.textContent = "Photograph my working again";
    }

    function removePhoto(button) {
      if (!submissionId) return;
      if (!window.confirm("Delete this photo and its feedback? This cannot be undone.")) {
        return;
      }

      button.disabled = true;
      button.textContent = "Deleting…";

      var body = new FormData();
      body.append("csrfmiddlewaretoken", csrf(root));

      fetch("/students/work/" + submissionId + "/delete/", {
        method: "POST",
        body: body,
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.success) throw new Error("refused");
          // Row and file are both gone -- the post_delete signal removes the
          // file -- so there is nothing left to show.
          feedbackEl.hidden = true;
          feedbackEl.innerHTML = "";
          submissionId = null;
          openBtn.textContent = "Photograph my working";
        })
        .catch(function () {
          button.disabled = false;
          button.textContent = "Delete this photo";
        });
    }

    function poll() {
      if (Date.now() - startedAt > POLL_LIMIT_MS) {
        stopPolling();
        say("Gave up waiting. Press the button again when you're ready.");
        openBtn.disabled = false;
        return;
      }

      fetch("/students/work/" + submissionId + "/status/", {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === "complete") return finish(data);
          if (data.status === "failed") {
            stopPolling();
            say(data.message || "That photo didn't come through clearly. Try again.");
            openBtn.disabled = false;
            return;
          }
          if (data.status === "analysing") say("Photo received — reading your working…");
          timer = window.setTimeout(poll, POLL_MS);
        })
        .catch(function () {
          timer = window.setTimeout(poll, POLL_MS);
        });
    }

    openBtn.addEventListener("click", function () {
      openBtn.disabled = true;
      feedbackEl.hidden = true;
      say("Getting a code…");
      panel.hidden = false;

      var body = new FormData();
      body.append("csrfmiddlewaretoken", csrf(root));
      body.append("part_type", partType);
      body.append("part_id", partId);

      fetch("/students/work/slot/", {
        method: "POST",
        body: body,
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.success) {
            say(data.message || "Couldn't start that. Try again in a moment.");
            openBtn.disabled = false;
            return;
          }
          submissionId = data.id;
          qrImg.src = data.qr;
          qrImg.hidden = false;
          if (linkEl) linkEl.textContent = data.upload_url;
          say("Scan this with your phone camera, then photograph your page.");
          startedAt = Date.now();
          stopPolling();
          timer = window.setTimeout(poll, POLL_MS);
        })
        .catch(function () {
          say("Couldn't reach NumScoil. Check your connection.");
          openBtn.disabled = false;
        });
    });

    if (cancelBtn) {
      cancelBtn.addEventListener("click", function () {
        stopPolling();
        panel.hidden = true;
        openBtn.disabled = false;
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-work-capture]"),
      wire
    );
  });
})();
