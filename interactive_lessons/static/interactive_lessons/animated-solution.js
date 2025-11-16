/**
 * AnimatedSolutionViewer - Step-by-step solution viewer with speech bubbles
 *
 * Features:
 * - Step-by-step navigation with Next/Previous buttons
 * - Speech bubble explanations with LaTeX support
 * - GeoGebra integration for interactive visualizations
 * - Drawing/image support
 * - Mathematical calculations with KaTeX rendering
 *
 * Usage:
 * const viewer = new AnimatedSolutionViewer('container-id', solutionData);
 */

class AnimatedSolutionViewer {
    constructor(containerId, solutionData) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }

        this.solutionData = solutionData;
        this.steps = solutionData.steps || [];
        this.currentStepIndex = 0;

        // Initialize
        this.render();
        this.showStep(0);
    }

    /**
     * Render the main structure
     */
    render() {
        this.container.innerHTML = `
            <div class="animated-solution-container">
                <div class="solution-header">
                    <h3 class="solution-title">${this.solutionData.title || 'Step-by-Step Solution'}</h3>
                    <div class="step-counter">
                        <span class="current-step">1</span> / <span class="total-steps">${this.steps.length}</span>
                    </div>
                </div>

                <div class="solution-content">
                    <!-- Speech bubble -->
                    <div class="speech-bubble">
                        <div class="speech-bubble-content"></div>
                    </div>

                    <!-- Main content area -->
                    <div class="step-visual-content"></div>
                </div>

                <div class="solution-navigation">
                    <button class="btn-prev" aria-label="Previous step">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"/>
                        </svg>
                        Previous
                    </button>

                    <div class="step-indicators"></div>

                    <button class="btn-next" aria-label="Next step">
                        Next
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        // Setup event listeners
        this.setupEventListeners();

        // Render step indicators
        this.renderStepIndicators();
    }

    /**
     * Setup event listeners for navigation
     */
    setupEventListeners() {
        const prevBtn = this.container.querySelector('.btn-prev');
        const nextBtn = this.container.querySelector('.btn-next');

        prevBtn.addEventListener('click', () => this.previousStep());
        nextBtn.addEventListener('click', () => this.nextStep());

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (this.container.querySelector('.animated-solution-container')) {
                if (e.key === 'ArrowLeft') this.previousStep();
                if (e.key === 'ArrowRight') this.nextStep();
            }
        });
    }

    /**
     * Render step indicators (dots)
     */
    renderStepIndicators() {
        const container = this.container.querySelector('.step-indicators');
        container.innerHTML = this.steps.map((_, index) => `
            <button
                class="step-indicator ${index === 0 ? 'active' : ''}"
                data-step="${index}"
                aria-label="Go to step ${index + 1}"
            ></button>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.step-indicator').forEach((indicator, index) => {
            indicator.addEventListener('click', () => this.showStep(index));
        });
    }

    /**
     * Show a specific step
     */
    showStep(index) {
        if (index < 0 || index >= this.steps.length) return;

        this.currentStepIndex = index;
        const step = this.steps[index];

        // Update counter
        this.container.querySelector('.current-step').textContent = index + 1;

        // Update indicators
        this.container.querySelectorAll('.step-indicator').forEach((indicator, i) => {
            indicator.classList.toggle('active', i === index);
        });

        // Update navigation buttons
        this.container.querySelector('.btn-prev').disabled = index === 0;
        this.container.querySelector('.btn-next').disabled = index === this.steps.length - 1;

        // Render speech bubble
        this.renderSpeechBubble(step);

        // Render step content
        this.renderStepContent(step);

        // Animate entry
        this.animateStepEntry();
    }

    /**
     * Render the speech bubble with explanation
     */
    renderSpeechBubble(step) {
        const bubble = this.container.querySelector('.speech-bubble-content');
        bubble.innerHTML = this.renderLatex(step.explanation);

        // Render math if KaTeX is available
        if (window.renderMathInElement) {
            window.renderMathInElement(bubble, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '$', right: '$', display: false}
                ],
                throwOnError: false
            });
        }
    }

    /**
     * Render the main content for the step
     */
    renderStepContent(step) {
        const contentArea = this.container.querySelector('.step-visual-content');

        switch (step.step_type) {
            case 'calculation':
                this.renderCalculation(contentArea, step);
                break;
            case 'drawing':
                this.renderDrawing(contentArea, step);
                break;
            case 'geogebra':
                this.renderGeoGebra(contentArea, step);
                break;
            default:
                this.renderText(contentArea, step);
        }
    }

    /**
     * Render text step
     */
    renderText(container, step) {
        container.innerHTML = `
            <div class="step-text-content">
                ${step.calculation ? `<div class="calculation-display">${this.renderLatex(step.calculation)}</div>` : ''}
            </div>
        `;

        if (window.renderMathInElement) {
            window.renderMathInElement(container, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false}
                ],
                throwOnError: false
            });
        }
    }

    /**
     * Render calculation step
     */
    renderCalculation(container, step) {
        container.innerHTML = `
            <div class="step-calculation">
                <div class="calculation-box">
                    ${this.renderLatex(step.calculation || '')}
                </div>
            </div>
        `;

        if (window.renderMathInElement) {
            window.renderMathInElement(container, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false}
                ],
                throwOnError: false
            });
        }
    }

    /**
     * Render drawing/image step
     */
    renderDrawing(container, step) {
        if (step.drawing_image) {
            container.innerHTML = `
                <div class="step-drawing">
                    <img src="${step.drawing_image}" alt="Step illustration" class="drawing-image">
                </div>
            `;
        } else {
            container.innerHTML = `<div class="step-text-content"><p>No drawing available</p></div>`;
        }
    }

    /**
     * Render GeoGebra interactive step
     */
    renderGeoGebra(container, step) {
        if (!step.geogebra_id) {
            container.innerHTML = `<div class="step-text-content"><p>No GeoGebra content available</p></div>`;
            return;
        }

        const geogebraId = `geogebra-${this.currentStepIndex}`;
        container.innerHTML = `
            <div class="step-geogebra">
                <div id="${geogebraId}" class="geogebra-container"></div>
            </div>
        `;

        // Load GeoGebra app
        this.loadGeoGebra(geogebraId, step.geogebra_id, step.geogebra_settings);
    }

    /**
     * Load GeoGebra app
     */
    loadGeoGebra(elementId, appId, settings = {}) {
        // Check if GeoGebra API is loaded
        if (typeof GGBApplet === 'undefined') {
            console.error('GeoGebra API not loaded');
            return;
        }

        const defaultSettings = {
            material_id: appId,
            width: 800,
            height: 600,
            showToolBar: false,
            showAlgebraInput: false,
            showMenuBar: false,
            enableRightClick: false,
            enableShiftDragZoom: true,
            showResetIcon: true,
            ...settings
        };

        const applet = new GGBApplet(defaultSettings, true);
        applet.inject(elementId);
    }

    /**
     * Render LaTeX text
     */
    renderLatex(text) {
        if (!text) return '';
        // Keep LaTeX delimiters intact for KaTeX to process
        return text;
    }

    /**
     * Animate step entry
     */
    animateStepEntry() {
        const bubble = this.container.querySelector('.speech-bubble');
        const content = this.container.querySelector('.step-visual-content');

        // Remove animation class
        bubble.classList.remove('animate-in');
        content.classList.remove('animate-in');

        // Trigger reflow
        void bubble.offsetWidth;
        void content.offsetWidth;

        // Add animation class
        bubble.classList.add('animate-in');
        content.classList.add('animate-in');
    }

    /**
     * Navigate to next step
     */
    nextStep() {
        if (this.currentStepIndex < this.steps.length - 1) {
            this.showStep(this.currentStepIndex + 1);
        }
    }

    /**
     * Navigate to previous step
     */
    previousStep() {
        if (this.currentStepIndex > 0) {
            this.showStep(this.currentStepIndex - 1);
        }
    }

    /**
     * Reset to first step
     */
    reset() {
        this.showStep(0);
    }

    /**
     * Destroy the viewer
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnimatedSolutionViewer;
}
