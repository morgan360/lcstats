// Live MathJax preview in Django admin for Notes
document.addEventListener("DOMContentLoaded", function () {
  const textarea = document.getElementById("id_content");
  if (!textarea) return;

  const preview = document.createElement("div");
  preview.id = "mathjax-preview";
  preview.style.marginTop = "20px";
  preview.style.padding = "10px";
  preview.style.background = "#f8f8f8";
  preview.style.border = "1px solid #ddd";
  preview.style.borderRadius = "6px";
  preview.innerHTML = "<em>Live preview will appear here...</em>";
  textarea.parentNode.appendChild(preview);

  const renderPreview = () => {
    preview.innerHTML = textarea.value;
    if (window.MathJax) MathJax.typesetPromise([preview]);
  };

  textarea.addEventListener("input", renderPreview);
  renderPreview();
});
