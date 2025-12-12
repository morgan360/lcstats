// Statistical Sampling Simulator
// Demonstrates the Central Limit Theorem through interactive visualization

// Global state
let state = {
    mean: 16,
    sd: 5,
    sampleSize: 5,
    sampleData: [],
    sampleMeans: [],
    samplesCount: 0,
    animationRunning: false,
    animationSpeed: 3,
    animationInterval: null
};

console.log('Stats Simulator v2.4 loaded successfully at:', new Date().toISOString());

// Box-Muller transform for generating normal random numbers
function randomNormal(mean, sd) {
    let u1 = Math.random();
    let u2 = Math.random();
    let z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    return z0 * sd + mean;
}

// Calculate statistical measures
function calculateStats(data) {
    if (data.length === 0) return { mean: 0, sd: 0, median: 0, skew: 0, kurtosis: 0 };

    const n = data.length;
    const mean = data.reduce((a, b) => a + b, 0) / n;

    const squaredDiffs = data.map(x => Math.pow(x - mean, 2));
    const variance = squaredDiffs.reduce((a, b) => a + b, 0) / n;
    const sd = Math.sqrt(variance);

    // Median
    const sorted = [...data].sort((a, b) => a - b);
    const median = n % 2 === 0
        ? (sorted[n/2 - 1] + sorted[n/2]) / 2
        : sorted[Math.floor(n/2)];

    // Skewness
    const cubedDiffs = data.map(x => Math.pow(x - mean, 3));
    const skew = sd > 0 ? (cubedDiffs.reduce((a, b) => a + b, 0) / n) / Math.pow(sd, 3) : 0;

    // Kurtosis (excess kurtosis)
    const fourthDiffs = data.map(x => Math.pow(x - mean, 4));
    const kurtosis = sd > 0 ? (fourthDiffs.reduce((a, b) => a + b, 0) / n) / Math.pow(sd, 4) - 3 : 0;

    return { mean, sd, median, skew, kurtosis };
}

// Generate normal distribution data for plotting
function generateNormalDistribution(mean, sd, numPoints = 1000) {
    const xMin = mean - 4 * sd;
    const xMax = mean + 4 * sd;
    const step = (xMax - xMin) / numPoints;

    const x = [];
    const y = [];

    for (let i = 0; i <= numPoints; i++) {
        const xi = xMin + i * step;
        x.push(xi);

        // Normal distribution PDF
        const exponent = -Math.pow(xi - mean, 2) / (2 * Math.pow(sd, 2));
        const yi = (1 / (sd * Math.sqrt(2 * Math.PI))) * Math.exp(exponent);
        y.push(yi);
    }

    return { x, y, xMin, xMax };
}

// Draw the parent population distribution (Graph 1)
function drawPopulation() {
    const { x, y } = generateNormalDistribution(state.mean, state.sd);

    const trace = {
        x: x,
        y: y,
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(128, 128, 128, 0.3)',
        line: { color: '#2C3E50', width: 3 },
        name: 'Population Distribution'
    };

    const layout = {
        title: {
            text: `Normal Distribution: μ=${state.mean}, σ=${state.sd}`,
            font: { size: 16, color: '#2C3E50' }
        },
        xaxis: {
            title: 'Value',
            gridcolor: '#E0E0E0'
        },
        yaxis: {
            title: 'Probability Density',
            gridcolor: '#E0E0E0'
        },
        plot_bgcolor: '#FAFAFA',
        paper_bgcolor: '#FFFFFF',
        margin: { t: 50, b: 50, l: 60, r: 30 }
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };

    Plotly.newPlot('populationPlot', [trace], layout, config);
}

// Draw sample data (Graph 2)
function drawSampleData() {
    if (state.sampleData.length === 0) {
        // Clear the plot if no data
        Plotly.newPlot('samplePlot', [], {
            title: 'Take a sample to see data points',
            xaxis: { title: 'Value' },
            yaxis: { visible: false, range: [0, 1] },
            plot_bgcolor: '#FAFAFA',
            paper_bgcolor: '#FFFFFF',
            margin: { t: 50, b: 50, l: 60, r: 30 }
        }, {
            responsive: true,
            displayModeBar: false
        });
        return;
    }

    // Create histogram for sample data
    const trace = {
        x: state.sampleData,
        type: 'histogram',
        marker: {
            color: '#3498DB',
            line: { color: '#2980B9', width: 1 }
        },
        name: 'Sample Data',
        nbinsx: Math.min(20, Math.max(5, Math.ceil(state.sampleData.length / 5)))
    };

    const stats = calculateStats(state.sampleData);

    const layout = {
        title: {
            text: `Sample Data (n=${state.sampleData.length})<br>Mean: ${stats.mean.toFixed(2)}, SD: ${stats.sd.toFixed(2)}`,
            font: { size: 14, color: '#2C3E50' }
        },
        xaxis: {
            title: 'Value',
            gridcolor: '#E0E0E0'
        },
        yaxis: {
            title: 'Frequency',
            gridcolor: '#E0E0E0'
        },
        plot_bgcolor: '#FAFAFA',
        paper_bgcolor: '#FFFFFF',
        margin: { t: 70, b: 50, l: 60, r: 30 },
        bargap: 0.05
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };

    Plotly.newPlot('samplePlot', [trace], layout, config);
}

// Draw distribution of sample means (Graph 3)
function drawSamplingDistribution() {
    if (state.sampleMeans.length === 0) {
        Plotly.newPlot('samplingDistributionPlot', [], {
            title: 'Take multiple samples to see the sampling distribution',
            xaxis: { title: 'Sample Mean' },
            yaxis: { title: 'Frequency' },
            plot_bgcolor: '#FAFAFA',
            paper_bgcolor: '#FFFFFF',
            margin: { t: 50, b: 50, l: 60, r: 30 }
        }, {
            responsive: true,
            displayModeBar: false
        });
        document.getElementById('cltInfo').style.display = 'none';
        return;
    }

    // Histogram of sample means
    const histogram = {
        x: state.sampleMeans,
        type: 'histogram',
        marker: {
            color: '#3498DB',
            line: { color: '#2980B9', width: 1 }
        },
        name: 'Sample Means',
        nbinsx: Math.min(30, Math.max(10, Math.ceil(state.sampleMeans.length / 10)))
    };

    // Theoretical normal distribution overlay
    const standardError = state.sd / Math.sqrt(state.sampleSize);
    const { x, y } = generateNormalDistribution(state.mean, standardError, 500);

    // Scale the theoretical distribution to match histogram
    const stats = calculateStats(state.sampleMeans);
    const histMax = state.sampleMeans.length * (x[1] - x[0]);
    const scaledY = y.map(yi => yi * histMax);

    const theoreticalCurve = {
        x: x,
        y: scaledY,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#E91E63', width: 3, dash: 'dash' },
        name: 'Theoretical Distribution'
    };

    const layout = {
        title: {
            text: `Distribution of Sample Means (${state.sampleMeans.length} samples)<br>Mean: ${stats.mean.toFixed(2)}, SE: ${stats.sd.toFixed(2)}`,
            font: { size: 14, color: '#2C3E50' }
        },
        xaxis: {
            title: 'Sample Mean',
            gridcolor: '#E0E0E0'
        },
        yaxis: {
            title: 'Frequency',
            gridcolor: '#E0E0E0'
        },
        plot_bgcolor: '#FAFAFA',
        paper_bgcolor: '#FFFFFF',
        margin: { t: 70, b: 50, l: 60, r: 30 },
        bargap: 0.05,
        showlegend: true,
        legend: { x: 0.7, y: 0.95 }
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };

    Plotly.newPlot('samplingDistributionPlot', [histogram, theoreticalCurve], layout, config);

    // Show CLT info if we have enough samples
    if (state.sampleMeans.length >= 5) {
        console.log('CLT Info Update - Sample count:', state.sampleMeans.length);
        console.log('Stats object:', stats);
        console.log('Observed SD:', stats.sd);
        console.log('State:', state);

        document.getElementById('cltInfo').style.display = 'block';

        const cltMeanElement = document.getElementById('cltMean');
        if (cltMeanElement) {
            cltMeanElement.textContent = state.mean;
        }

        // Theoretical SE
        const theoreticalSE = state.sd / Math.sqrt(state.sampleSize);

        // Population mean (μ)
        const populationMeanElement = document.getElementById('populationMean');
        if (populationMeanElement) {
            populationMeanElement.textContent = state.mean.toFixed(2);
            console.log('Set population mean to:', state.mean);
        }

        // Observed mean of sample means
        const observedMeanElement = document.getElementById('observedMean');
        if (observedMeanElement) {
            observedMeanElement.textContent = stats.mean.toFixed(3);
            console.log('Set observed mean to:', stats.mean.toFixed(3));
        }

        // Observed SD of sample means
        const observedSDElement = document.getElementById('observedSD');
        console.log('observedSD element:', observedSDElement);
        if (observedSDElement) {
            observedSDElement.textContent = stats.sd.toFixed(3);
            console.log('Set observedSD to:', stats.sd.toFixed(3));
        }

        // SE Formula and calculation
        const seFormulaElement = document.getElementById('seFormula');
        const seCalcElement = document.getElementById('seCalculation');
        console.log('seFormula element:', seFormulaElement);
        console.log('seCalculation element:', seCalcElement);

        if (seFormulaElement) {
            seFormulaElement.textContent = `σ/√n = ${state.sd}/√${state.sampleSize}`;
            console.log('Set formula to:', `σ/√n = ${state.sd}/√${state.sampleSize}`);
        }
        if (seCalcElement) {
            seCalcElement.textContent = theoreticalSE.toFixed(3);
            console.log('Set calculation to:', theoreticalSE.toFixed(3));
        }
    }
}

// Take a sample from the population
function takeSample() {
    const sample = [];
    for (let i = 0; i < state.sampleSize; i++) {
        sample.push(randomNormal(state.mean, state.sd));
    }

    state.sampleData = sample;
    const sampleMean = sample.reduce((a, b) => a + b, 0) / sample.length;
    state.sampleMeans.push(sampleMean);
    state.samplesCount++;

    updateStatistics();
    drawSampleData();
    drawSamplingDistribution();
}

// Update statistics display
function updateStatistics() {
    document.getElementById('samplesCount').textContent = state.samplesCount;

    if (state.sampleData.length > 0) {
        const stats = calculateStats(state.sampleData);
        document.getElementById('sampleMean').textContent = stats.mean.toFixed(3);
        document.getElementById('sampleSd').textContent = stats.sd.toFixed(3);

        const standardError = state.sd / Math.sqrt(state.sampleSize);
        document.getElementById('standardError').textContent = standardError.toFixed(3);
    } else {
        document.getElementById('sampleMean').textContent = '—';
        document.getElementById('sampleSd').textContent = '—';
        document.getElementById('standardError').textContent = '—';
    }
}

// Clear all data and reset
function clearAll() {
    state.sampleData = [];
    state.sampleMeans = [];
    state.samplesCount = 0;

    stopAnimation();

    drawPopulation();
    drawSampleData();
    drawSamplingDistribution();
    updateStatistics();
}

// Animation functions
function startAnimation() {
    if (state.animationRunning) return;

    state.animationRunning = true;
    document.getElementById('playAnimation').style.display = 'none';
    document.getElementById('pauseAnimation').style.display = 'inline-block';
    document.getElementById('animationControls').style.display = 'flex';

    const delay = 1000 / state.animationSpeed;

    state.animationInterval = setInterval(() => {
        takeSample();
    }, delay);
}

function stopAnimation() {
    if (!state.animationRunning) return;

    state.animationRunning = false;
    document.getElementById('playAnimation').style.display = 'inline-block';
    document.getElementById('pauseAnimation').style.display = 'none';

    if (state.animationInterval) {
        clearInterval(state.animationInterval);
        state.animationInterval = null;
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize
    drawPopulation();
    drawSampleData();
    drawSamplingDistribution();
    updateStatistics();

    // Input controls
    document.getElementById('meanInput').addEventListener('change', function() {
        state.mean = parseFloat(this.value);
        document.getElementById('displayMean').textContent = state.mean;
        drawPopulation();
    });

    document.getElementById('sdInput').addEventListener('change', function() {
        const newSd = parseFloat(this.value);
        if (newSd > 0) {
            state.sd = newSd;
            document.getElementById('displaySd').textContent = state.sd;
            drawPopulation();
        } else {
            alert('Standard deviation must be greater than 0');
            this.value = state.sd;
        }
    });

    document.getElementById('sampleSize').addEventListener('change', function() {
        state.sampleSize = parseInt(this.value);
    });

    // Button controls
    document.getElementById('generateSample').addEventListener('click', takeSample);
    document.getElementById('clearAll').addEventListener('click', clearAll);
    document.getElementById('playAnimation').addEventListener('click', startAnimation);
    document.getElementById('pauseAnimation').addEventListener('click', stopAnimation);

    // Animation speed control
    document.getElementById('animationSpeed').addEventListener('input', function() {
        state.animationSpeed = parseInt(this.value);
        document.getElementById('speedDisplay').textContent = state.animationSpeed + 'x';

        // If animation is running, restart it with new speed
        if (state.animationRunning) {
            stopAnimation();
            startAnimation();
        }
    });

    // Help modal
    const modal = document.getElementById('helpModal');
    const helpButton = document.getElementById('helpButton');
    const closeButton = document.querySelector('.close');
    const closeHelpButton = document.getElementById('closeHelp');

    helpButton.addEventListener('click', function() {
        modal.style.display = 'block';
    });

    closeButton.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    closeHelpButton.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            modal.style.display = 'none';
            stopAnimation();
        } else if (event.key === ' ' && event.target.tagName !== 'INPUT') {
            event.preventDefault();
            if (state.animationRunning) {
                stopAnimation();
            } else {
                startAnimation();
            }
        } else if (event.key === 'Enter' && event.target.tagName !== 'INPUT') {
            takeSample();
        } else if (event.key === 'c' && event.ctrlKey) {
            clearAll();
        }
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        Plotly.Plots.resize('populationPlot');
        Plotly.Plots.resize('samplePlot');
        Plotly.Plots.resize('samplingDistributionPlot');
    });
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopAnimation();
});
