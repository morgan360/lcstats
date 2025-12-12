# Statistical Sampling Simulator

An interactive web-based tool for demonstrating the Central Limit Theorem (CLT) through dynamic visualizations.

## Overview

This Django app provides a visual, hands-on way for students to understand statistical sampling distributions and the Central Limit Theorem. Users can specify a normal distribution, take samples from it, and watch as the distribution of sample means converges to a normal distribution.

## Features

### Three Interactive Graphs

1. **Parent Population Distribution**
   - Visual representation of the normal distribution being sampled from
   - Dynamically updates when mean or standard deviation changes
   - Shows PDF (Probability Density Function) curve

2. **Sample Data**
   - Displays data points from the most recent sample
   - Shows as histogram with calculated statistics
   - Updates with each new sample taken

3. **Distribution of Sample Means**
   - Histogram showing all sample means collected
   - Overlays theoretical normal distribution curve
   - Demonstrates CLT convergence visually

### Controls

- **Population Parameters**:
  - Mean (μ): Adjustable from -100 to 100 (default: 16)
  - Standard Deviation (σ): Adjustable from 0.1 to 50 (default: 5)

- **Sample Size (n)**: Choose from 1, 5, 10, 100, 1000, or 10,000 samples

- **Actions**:
  - Generate Sample: Take one sample
  - Clear All: Reset all data and graphs
  - Play Animation: Automatically take repeated samples
  - Pause: Stop the animation
  - Animation Speed: Control sampling rate (1x to 10x)

### Educational Features

- **Real-time Statistics Display**:
  - Number of samples taken
  - Sample mean and standard deviation
  - Standard error of the mean (SE = σ/√n)

- **Interactive Help System**:
  - Comprehensive help modal explaining CLT
  - Tooltips on graphs explaining concepts
  - Step-by-step tutorial suggestions

- **Visual CLT Indicators**:
  - Theoretical distribution overlay on sampling distribution
  - Information box showing CLT convergence
  - Color-coded graphs for easy understanding

### Keyboard Shortcuts

- **Space**: Play/Pause animation
- **Enter**: Generate single sample
- **Ctrl+C**: Clear all data
- **Escape**: Close help modal or stop animation

## Technical Implementation

### Technology Stack

- **Frontend**:
  - Plotly.js for interactive charts
  - Vanilla JavaScript (no frameworks)
  - CSS3 with responsive design

- **Backend**:
  - Django 5.2.7
  - No database models (client-side only)
  - Single view serving the template

### Statistical Methods

1. **Random Number Generation**:
   - Box-Muller transform for normal distribution
   - Produces high-quality random normal variates

2. **Calculations**:
   - Mean, median, standard deviation
   - Skewness and kurtosis (for future features)
   - Standard error: SE = σ/√n
   - Normal PDF: f(x) = (1/σ√(2π)) * e^(-(x-μ)²/(2σ²))

3. **Visualization**:
   - Adaptive histogram binning
   - Theoretical distribution scaling
   - Smooth curve rendering

## File Structure

```
stats_simulator/
├── __init__.py
├── apps.py
├── views.py
├── urls.py
├── models.py (empty)
├── admin.py (empty)
├── templates/
│   └── stats_simulator/
│       └── index.html
├── static/
│   └── stats_simulator/
│       ├── simulator.js
│       └── styles.css
└── README.md
```

## Usage

### Access the Simulator

Navigate to: `http://127.0.0.1:8000/stats-simulator/`

### Basic Workflow

1. **Set Population Parameters**:
   - Adjust mean and standard deviation as desired
   - The parent population graph updates automatically

2. **Choose Sample Size**:
   - Select how many values per sample (n)
   - Larger n → narrower sampling distribution

3. **Take Samples**:
   - Click "Generate Sample" for single samples
   - Or click "Play Animation" for automatic sampling
   - Watch Graph 3 develop to show CLT

4. **Observe CLT**:
   - Notice the sampling distribution forms a bell curve
   - Center is at population mean (μ)
   - Spread decreases with larger sample size
   - Pink dashed line shows theoretical distribution

5. **Experiment**:
   - Change parameters and clear to see effects
   - Try different sample sizes (compare n=5 vs n=100)
   - Take many samples (1000+) to see strong convergence

## Educational Objectives

Students using this tool will learn:

1. **Central Limit Theorem**:
   - Sample means form a normal distribution
   - True regardless of population shape (here we use normal)
   - Convergence improves with more samples

2. **Standard Error Concept**:
   - SE = σ/√n
   - Larger sample size → smaller standard error
   - Relates to precision of estimates

3. **Sampling Variability**:
   - Individual samples vary from population
   - Sample means vary less than individual values
   - Law of large numbers in action

4. **Statistical Inference Foundation**:
   - Basis for confidence intervals
   - Understanding hypothesis testing
   - Practical meaning of "sampling distribution"

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Responsive design (graphs stack vertically)

## Performance Notes

- Efficiently handles up to 10,000 samples per click
- Animation runs smoothly at up to 10x speed
- Plotly.js provides GPU-accelerated rendering
- No backend load (all calculations client-side)

## Future Enhancements (Potential)

- [ ] Support for non-normal parent distributions (uniform, exponential, etc.)
- [ ] Export functionality (download charts as PNG, data as CSV)
- [ ] Comparison mode (side-by-side with different parameters)
- [ ] More statistical measures (confidence intervals, p-values)
- [ ] Save/load configurations
- [ ] Embedding capability for other pages

## Integration with LCAI Maths

This tool is part of the LCAI Maths educational platform for Leaving Certificate Higher Level Mathematics students. It specifically supports:

- **Topic**: Statistics and Probability
- **Learning Outcomes**: Understanding sampling distributions, CLT
- **Curriculum Alignment**: LC Higher Level Statistics strand

To add to navigation, edit `templates/_base.html` and add a link under the "Study" dropdown menu.

## Accessibility

- Keyboard navigation support
- Screen-reader friendly labels
- High contrast mode compatible
- Responsive text sizing
- Touch-friendly controls for mobile

## Credits

- Statistical methods: Standard textbook implementations
- Visualization: Plotly.js library
- UI/UX: Custom design matching LCAI Maths theme
- Box-Muller transform: Standard algorithm for normal random generation

## License

Part of the LCAI Maths project. For educational use.
