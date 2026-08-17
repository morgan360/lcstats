/*
 * Shared log tables viewer.
 *
 * Renders the Formulae and Tables booklet with PDF.js and overlays clickable
 * link areas on the booklet's own contents spread, so a student navigates it the
 * same way they will navigate the paper copy in the exam: open the contents,
 * read down it, go to the page. Nothing here jumps anywhere on the student's
 * behalf.
 *
 * Used by the full page (cheatsheets/log_tables.html) and by the floating panel
 * on question pages (includes/log_tables_panel.html).
 */

const PDFJS_BASE = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/legacy/build/";

let pdfjsPromise = null;

function loadPdfJs() {
    if (!pdfjsPromise) {
        pdfjsPromise = import(PDFJS_BASE + "pdf.min.mjs").then((lib) => {
            lib.GlobalWorkerOptions.workerSrc = PDFJS_BASE + "pdf.worker.min.mjs";
            return lib;
        });
    }
    return pdfjsPromise;
}

export async function initLogTablesViewer(root, config) {
    const el = (name) => root.querySelector(`[data-lt="${name}"]`);

    const canvas = el("canvas");
    const overlay = el("overlay");
    const stage = el("stage");
    const scroller = el("scroll");
    const status = el("status");
    const fallback = el("fallback");
    const fallbackLink = el("fallback-link");
    const pageInput = el("page");
    const prevBtn = el("prev");
    const nextBtn = el("next");
    const contentsBtn = el("contents");

    const contentsLinks = config.contentsLinks || {};
    const contentsPages = config.contentsPages || [];

    let pdfDoc = null;
    let currentPage = config.startPage;
    let zoom = 1;
    let renderTask = null;
    let renderToken = 0;

    const toPrinted = (pdfPage) => pdfPage - config.pageOffset;
    const toPdf = (printed) => printed + config.pageOffset;
    const inBookletRange = (printed) =>
        printed >= config.firstPrinted && printed <= config.lastPrinted;

    /* ---------- contents links ---------- */

    function drawOverlay() {
        overlay.textContent = "";
        const links = contentsLinks[currentPage];
        if (!links) {
            overlay.hidden = true;
            return;
        }
        overlay.hidden = false;
        links.forEach((link) => {
            const hotspot = document.createElement("button");
            hotspot.type = "button";
            hotspot.className = "lt-hotspot";
            hotspot.style.left = link.x * 100 + "%";
            hotspot.style.top = link.y * 100 + "%";
            hotspot.style.width = link.w * 100 + "%";
            hotspot.style.height = link.h * 100 + "%";
            hotspot.title = `${link.title_en} - page ${link.printed_page}`;
            hotspot.setAttribute(
                "aria-label",
                `${link.title_en} (${link.title_ga}), page ${link.printed_page}`
            );
            hotspot.addEventListener("click", () => goToPage(link.target));
            overlay.appendChild(hotspot);
        });
    }

    /* ---------- rendering ---------- */

    async function render() {
        if (!pdfDoc) return;
        const token = ++renderToken;

        if (renderTask) {
            renderTask.cancel();
            renderTask = null;
        }

        const page = await pdfDoc.getPage(currentPage);
        if (token !== renderToken) return;

        const unscaled = page.getViewport({ scale: 1 });

        /* Booklet pages are landscape, so fitting the width alone would push the
           bottom of the page below the fold. Fit both dimensions instead: at
           zoom 1 the whole page is visible, and zooming in scrolls as usual. */
        const availableWidth = Math.max(scroller.clientWidth - 24, 200);
        const availableHeight = Math.max(scroller.clientHeight - 24, 200);
        const fitScale = Math.min(
            availableWidth / unscaled.width,
            availableHeight / unscaled.height
        );
        const viewport = page.getViewport({ scale: fitScale * zoom });

        // Render at device resolution so dense number tables stay legible.
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = Math.floor(viewport.width) + "px";
        canvas.style.height = Math.floor(viewport.height) + "px";
        stage.style.width = Math.floor(viewport.width) + "px";

        renderTask = page.render({
            canvasContext: canvas.getContext("2d"),
            viewport,
            transform: dpr === 1 ? null : [dpr, 0, 0, dpr, 0, 0],
        });
        try {
            await renderTask.promise;
        } catch (err) {
            if (err && err.name === "RenderingCancelledException") return;
            throw err;
        }
        renderTask = null;
    }

    function syncControls() {
        const printed = toPrinted(currentPage);
        if (pageInput) pageInput.value = inBookletRange(printed) ? printed : "";
        if (prevBtn) prevBtn.disabled = currentPage <= 1;
        if (nextBtn) nextBtn.disabled = Boolean(pdfDoc) && currentPage >= pdfDoc.numPages;
        if (fallbackLink) fallbackLink.href = config.pdfUrl + "#page=" + currentPage;
        if (contentsBtn) contentsBtn.disabled = contentsPages.includes(currentPage);

        if (config.syncUrl) {
            const url = new URL(window.location.href);
            if (inBookletRange(printed)) {
                url.searchParams.set("page", printed);
            } else {
                url.searchParams.delete("page");
            }
            window.history.replaceState(null, "", url);
        }
    }

    function goToPage(pdfPage) {
        if (!pdfDoc) return;
        currentPage = Math.min(Math.max(pdfPage, 1), pdfDoc.numPages);
        scroller.scrollTop = 0;
        syncControls();
        drawOverlay();
        render();
    }

    /* ---------- controls ---------- */

    if (prevBtn) prevBtn.addEventListener("click", () => goToPage(currentPage - 1));
    if (nextBtn) nextBtn.addEventListener("click", () => goToPage(currentPage + 1));
    if (contentsBtn) contentsBtn.addEventListener("click", () => goToPage(contentsPages[0]));

    if (pageInput) {
        pageInput.addEventListener("change", () => {
            const printed = Number(pageInput.value);
            if (Number.isInteger(printed) && inBookletRange(printed)) {
                goToPage(toPdf(printed));
            } else {
                syncControls();
            }
        });
    }

    function setZoom(next) {
        zoom = Math.min(Math.max(next, 0.5), 4);
        render();
    }
    const zoomIn = el("zoom-in");
    const zoomOut = el("zoom-out");
    const zoomReset = el("zoom-reset");
    if (zoomIn) zoomIn.addEventListener("click", () => setZoom(zoom * 1.25));
    if (zoomOut) zoomOut.addEventListener("click", () => setZoom(zoom / 1.25));
    if (zoomReset) zoomReset.addEventListener("click", () => setZoom(1));  // back to whole page

    if (config.keyboardNav) {
        document.addEventListener("keydown", (event) => {
            if (event.target.matches("input, textarea")) return;
            if (event.key === "ArrowLeft" || event.key === "PageUp") goToPage(currentPage - 1);
            if (event.key === "ArrowRight" || event.key === "PageDown") goToPage(currentPage + 1);
        });
    }

    let resizeTimer = null;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(render, 150);
    });

    /* ---------- boot ---------- */

    try {
        const pdfjsLib = await loadPdfJs();
        pdfDoc = await pdfjsLib.getDocument(config.pdfUrl).promise;
        currentPage = Math.min(currentPage, pdfDoc.numPages);
        if (status) status.hidden = true;
        syncControls();
        drawOverlay();
        await render();
    } catch (err) {
        console.error("Log tables viewer failed to load", err);
        if (status) status.hidden = true;
        if (stage) stage.hidden = true;
        if (fallbackLink) fallbackLink.href = config.pdfUrl + "#page=" + currentPage;
        if (fallback) fallback.hidden = false;
    }

    return { goToPage, refresh: render };
}
