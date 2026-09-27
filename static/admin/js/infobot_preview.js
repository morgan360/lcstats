/* Render the maths in an InfoBot answer's preview on its admin page, with the
 * same delimiters the student's AI Help panel uses (static/js/feedback_render.js).
 */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.infobot-preview').forEach(function (el) {
    window.Feedback.renderMaths(el);
  });
});
