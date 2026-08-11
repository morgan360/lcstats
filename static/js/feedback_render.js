/* Shared rendering for content that arrives after the page has loaded.
 *
 * Two jobs, both of which were copied by hand into nearly a dozen places
 * before this file existed:
 *
 *   tidy()        - graders are told to return plain prose with $...$ maths,
 *                   but model output is never guaranteed, so stray Markdown
 *                   emphasis gets rendered rather than shown to a student as
 *                   literal asterisks.
 *   renderMaths() - the base template's KaTeX pass runs once on load and is
 *                   long gone by the time feedback comes back, so anything
 *                   injected afterwards has to be rendered explicitly.
 *
 * Loaded from _base.html, so it is available to every page that extends it.
 * The phone upload page deliberately does not extend _base and keeps its own
 * copy -- see students/templates/students/work_mobile.html.
 */
(function (window) {
  "use strict";

  /* The app-wide set. _base.html runs this same list over the whole document
   * on load, so injected fragments using it is what stops one piece of maths
   * rendering differently depending on whether it arrived with the page or
   * after it.
   */
  var DELIMITERS = [
    { left: "$$", right: "$$", display: true },
    { left: "\\[", right: "\\]", display: true },
    { left: "\\(", right: "\\)", display: false },
    { left: "$", right: "$", display: false }
  ];

  /* Not a Markdown parser and not a sanitiser -- three replacements over text
   * the server has already produced. Anything needing real safety guarantees
   * should be escaped by its caller before it gets here.
   */
  function tidy(text) {
    return (text || "")
      .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\n]+?)\*(?=[\s.,;:)]|$)/g, "$1<em>$2</em>");
  }

  /* Safe to call when KaTeX has not loaded or the element is missing: the text
   * keeps its dollars and stays readable, which is how every call site behaved
   * before this was shared. Returns whether it actually rendered.
   */
  function renderMaths(element) {
    if (!element || !window.renderMathInElement) return false;
    try {
      window.renderMathInElement(element, {
        delimiters: DELIMITERS,
        throwOnError: false
      });
      return true;
    } catch (e) {
      // A maths error must never take the feedback down with it.
      return false;
    }
  }

  window.Feedback = {
    tidy: tidy,
    renderMaths: renderMaths,
    DELIMITERS: DELIMITERS
  };
})(window);
