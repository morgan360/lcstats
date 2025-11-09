// Debug script for InfoBot - paste this into browser console
console.log("=== InfoBot Debug ===");
console.log("1. Checking elements:");
console.log("  - infobotQueryInput:", document.getElementById("infobot-query"));
console.log("  - infobotAskBtn:", document.getElementById("infobot-ask-btn"));
console.log("  - infobotAnswer:", document.getElementById("infobot-answer"));
console.log("  - infobotLoading:", document.getElementById("infobot-loading"));
console.log("  - topicSlug element:", document.querySelector("[data-topic-slug]"));
if (document.querySelector("[data-topic-slug]")) {
  console.log("  - topicSlug value:", document.querySelector("[data-topic-slug]").dataset.topicSlug);
}

console.log("\n2. Testing manual click:");
const btn = document.getElementById("infobot-ask-btn");
if (btn) {
  console.log("  - Button found, event listeners:", getEventListeners(btn));
} else {
  console.log("  - Button NOT found!");
}

console.log("\n3. Checking if quiz.js loaded:");
console.log("  - DOMContentLoaded listeners:", getEventListeners(document));
