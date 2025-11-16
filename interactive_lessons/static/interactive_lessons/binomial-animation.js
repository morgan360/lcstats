/**
 * Binomial Distribution Basketball Animation
 * Animates basketball free throw sequences for probability problems
 */

class BasketballAnimation {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        this.options = {
            width: options.width || 800,
            height: options.height || 400,
            throwDuration: options.throwDuration || 800,
            pauseBetweenThrows: options.pauseBetweenThrows || 500,
            showSteps: options.showSteps !== false,
            ...options
        };

        this.canvas = null;
        this.ctx = null;
        this.isAnimating = false;
        this.currentStep = 0;

        this.init();
    }

    init() {
        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.options.width;
        this.canvas.height = this.options.height;
        this.canvas.style.border = '2px solid #004aad';
        this.canvas.style.borderRadius = '8px';
        this.canvas.style.backgroundColor = '#f8f9fa';
        this.ctx = this.canvas.getContext('2d');

        // Create controls container
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'animation-controls';
        controlsDiv.style.cssText = 'margin-top: 15px; display: flex; gap: 10px; justify-content: center;';

        // Create info panel
        this.infoPanel = document.createElement('div');
        this.infoPanel.className = 'animation-info';
        this.infoPanel.style.cssText = `
            margin-top: 15px;
            padding: 15px;
            background: white;
            border: 2px solid #004aad;
            border-radius: 8px;
            font-family: Arial, sans-serif;
            line-height: 1.6;
        `;

        // Append to container
        this.container.appendChild(this.canvas);
        this.container.appendChild(controlsDiv);
        this.container.appendChild(this.infoPanel);

        // Draw initial state
        this.drawCourt();
    }

    drawCourt() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, w, h);

        // Draw basketball hoop
        const hoopX = w - 100;
        const hoopY = h / 2 - 50;

        // Backboard
        ctx.fillStyle = '#333';
        ctx.fillRect(hoopX + 50, hoopY - 40, 5, 100);

        // Rim
        ctx.strokeStyle = '#ff6600';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(hoopX, hoopY + 20, 25, 0, Math.PI * 2);
        ctx.stroke();

        // Net
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        for (let i = 0; i < 8; i++) {
            const angle = (Math.PI * 2 * i) / 8;
            const x1 = hoopX + Math.cos(angle) * 25;
            const y1 = hoopY + 20 + Math.sin(angle) * 25;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(hoopX, hoopY + 60);
            ctx.stroke();
        }

        // Player position indicator
        ctx.fillStyle = '#004aad';
        ctx.font = 'bold 16px Arial';
        ctx.fillText('🏀 Player', 50, h / 2 + 80);
    }

    drawBall(x, y, size = 20) {
        const ctx = this.ctx;

        // Basketball
        ctx.fillStyle = '#ff6600';
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();

        // Black lines
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.stroke();

        // Seams
        ctx.beginPath();
        ctx.moveTo(x - size, y);
        ctx.lineTo(x + size, y);
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(x, y, size, Math.PI * 0.3, Math.PI * 0.7);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x, y, size, Math.PI * 1.3, Math.PI * 1.7);
        ctx.stroke();
    }

    async animateThrow(startX, startY, endX, endY, isMake) {
        return new Promise((resolve) => {
            const duration = this.options.throwDuration;
            const startTime = Date.now();

            // Calculate arc parameters
            const midX = (startX + endX) / 2;
            const midY = Math.min(startY, endY) - 150; // Arc height

            const animate = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Redraw court
                this.drawCourt();

                // Quadratic bezier curve for arc
                const t = progress;
                const x = (1 - t) * (1 - t) * startX + 2 * (1 - t) * t * midX + t * t * endX;
                const y = (1 - t) * (1 - t) * startY + 2 * (1 - t) * t * midY + t * t * endY;

                // Draw trajectory path
                this.ctx.strokeStyle = 'rgba(0, 74, 173, 0.3)';
                this.ctx.lineWidth = 2;
                this.ctx.setLineDash([5, 5]);
                this.ctx.beginPath();
                this.ctx.moveTo(startX, startY);
                this.ctx.quadraticCurveTo(midX, midY, endX, endY);
                this.ctx.stroke();
                this.ctx.setLineDash([]);

                // Draw ball
                this.drawBall(x, y);

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    // Show result
                    if (isMake) {
                        this.showResult(endX, endY, '✓ MAKE', '#00994c');
                    } else {
                        this.showResult(endX + 40, endY, '✗ MISS', '#cc0000');
                    }
                    resolve();
                }
            };

            animate();
        });
    }

    showResult(x, y, text, color) {
        this.ctx.fillStyle = color;
        this.ctx.font = 'bold 24px Arial';
        this.ctx.fillText(text, x - 30, y - 30);
    }

    async animateSequence(sequence, scenario) {
        if (this.isAnimating) return;
        this.isAnimating = true;

        const hoopX = this.canvas.width - 100;
        const hoopY = this.canvas.height / 2 - 50;
        const startX = 100;
        const startY = this.canvas.height / 2 + 50;

        this.updateInfo(scenario, 0, sequence.length);

        for (let i = 0; i < sequence.length; i++) {
            const isMake = sequence[i];

            // Animate throw
            const endX = isMake ? hoopX : hoopX + 40;
            const endY = isMake ? hoopY + 20 : hoopY - 40;

            this.currentStep = i + 1;
            this.updateInfo(scenario, i + 1, sequence.length);

            await this.animateThrow(startX, startY, endX, endY, isMake);

            // Pause between throws
            if (i < sequence.length - 1) {
                await this.sleep(this.options.pauseBetweenThrows);
            }
        }

        // Show final calculation
        await this.sleep(500);
        this.showCalculation(scenario);

        this.isAnimating = false;
    }

    updateInfo(scenario, currentThrow, totalThrows) {
        const throws = currentThrow > 0 ? `Throw ${currentThrow} of ${totalThrows}` : 'Ready to start';

        this.infoPanel.innerHTML = `
            <div style="margin-bottom: 10px;">
                <strong style="color: #004aad; font-size: 18px;">Scenario ${scenario.part}</strong>
            </div>
            <div style="margin-bottom: 8px;">
                ${scenario.description}
            </div>
            <div style="margin-bottom: 8px;">
                <strong>Current Status:</strong> ${throws}
            </div>
            <div style="color: #666; font-size: 14px;">
                p = ${scenario.p} (success) | q = ${scenario.q} (failure)
            </div>
        `;
    }

    showCalculation(scenario) {
        const calcDiv = document.createElement('div');
        calcDiv.style.cssText = `
            margin-top: 15px;
            padding: 15px;
            background: #f0f7ff;
            border-left: 4px solid #004aad;
            animation: slideIn 0.5s ease;
        `;

        calcDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px; color: #004aad;">
                Calculation:
            </div>
            ${scenario.steps.map((step, i) => `
                <div style="margin: 5px 0; animation: fadeIn 0.5s ease ${i * 0.2}s both;">
                    <strong>Step ${i + 1}:</strong> ${step}
                </div>
            `).join('')}
            <div style="margin-top: 15px; padding: 10px; background: #00994c; color: white; border-radius: 4px; font-weight: bold; animation: fadeIn 0.5s ease ${scenario.steps.length * 0.2}s both;">
                Answer: ${scenario.answer}
            </div>
        `;

        this.infoPanel.appendChild(calcDiv);
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    reset() {
        this.drawCourt();
        this.infoPanel.innerHTML = '<div style="color: #666;">Select a scenario to begin animation</div>';
        this.isAnimating = false;
        this.currentStep = 0;
    }
}

// Scenario definitions for the basketball example
const basketballScenarios = {
    scenario1: {
        part: 'i',
        description: 'Misses for the 1st time on his 5th free throw',
        sequence: [true, true, true, true, false], // 4 makes, then 1 miss
        p: 0.8,
        q: 0.2,
        steps: [
            'No. of Trials: n = 5',
            'p = 0.8 and q = 1 – 0.8 = 0.2',
            'r = 4 (number of successes)',
            'P(4) = (0.8)⁴(0.2)¹ = 0.08192'
        ],
        answer: 'P(misses on 5th) = 0.08192 or 8.192%'
    },
    scenario2: {
        part: 'ii',
        description: 'Makes his 1st basket on the 4th free throw',
        sequence: [false, false, false, true], // 3 misses, then 1 make
        p: 0.2,
        q: 0.8,
        steps: [
            'No. of Trials: n = 4',
            'p = 0.2 and q = 1 – 0.2 = 0.8 (success = miss)',
            'r = 3 (number of misses before success)',
            'P(3) = (0.2)³(0.8)¹ = 0.0064'
        ],
        answer: 'P(1st make on 4th) = 0.0064 or 0.64%'
    },
    scenario3: {
        part: 'iii',
        description: 'Makes 1st basket on one of his first 3 free throws',
        sequence: [true, false, false], // Example: makes on 1st throw
        p: 0.8,
        q: 0.2,
        steps: [
            'No. of Trials: n = 3',
            'p = 0.8 and q = 1 – 0.8 = 0.2',
            'r = 1 (exactly 1 success)',
            'P(1) = ₃C₁(0.8)¹(0.2)² = 3 × 0.8 × 0.04 = 0.096'
        ],
        answer: 'P(exactly 1 make in 3 throws) = 0.096 or 9.6%'
    }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { BasketballAnimation, basketballScenarios };
}
