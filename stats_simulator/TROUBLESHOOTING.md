# Troubleshooting Guide - Stats Simulator

## Issue: Values Not Displaying in CLT Info Box

### Symptoms
- Graph 3 shows histogram correctly
- Green CLT info box appears
- But boxes show "—" instead of calculated values
- Screenshot shows:
  - "OBSERVED SD OF SAMPLE MEANS: —"
  - "SE CALCULATION: — = —"

### Common Causes

#### 1. Browser Cache (Most Likely)
**Problem**: Browser is serving old JavaScript/CSS files

**Solution**:
1. **Hard Refresh** the page:
   - **Windows/Linux**: `Ctrl + Shift + R` or `Ctrl + F5`
   - **Mac**: `Cmd + Shift + R`

2. **Clear Cache** for the site:
   - Chrome: DevTools → Network tab → "Disable cache" checkbox
   - Firefox: DevTools → Network tab → gear icon → "Disable HTTP cache"
   - Safari: Develop → Empty Caches

3. **Verify Version Loading**:
   - Open DevTools (F12)
   - Go to Network tab
   - Reload page
   - Check if `simulator.js?v=2.0` appears (not just `simulator.js`)

#### 2. JavaScript Not Loading
**Problem**: Script file not found or not executing

**Solution**:
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Look for messages like:
   - "Failed to load resource: simulator.js"
   - "Uncaught ReferenceError"
   - "Cannot read property of undefined"

4. If errors appear, check:
   - File exists: `stats_simulator/static/stats_simulator/simulator.js`
   - Django static files served: `python manage.py collectstatic` (if in production)

#### 3. Timing Issue
**Problem**: JavaScript runs before Plotly loads

**Solution**:
- Already handled in code (DOMContentLoaded event)
- But check console for errors about "Plotly is not defined"

#### 4. Element IDs Mismatch
**Problem**: HTML element IDs don't match JavaScript selectors

**Verification** - These should match:

**HTML** (in `index.html`):
```html
<span id="observedSD">—</span>
<span id="seFormula">—</span>
<span id="seCalculation">—</span>
```

**JavaScript** (in `simulator.js`):
```javascript
document.getElementById('observedSD').textContent = ...
document.getElementById('seFormula').textContent = ...
document.getElementById('seCalculation').textContent = ...
```

✅ All IDs match correctly in current version

## Verification Steps

### Step 1: Check JavaScript Console
1. Open page: http://127.0.0.1:8000/stats-simulator/
2. Press F12 (or Cmd+Option+I on Mac)
3. Go to Console tab
4. Look for any red error messages
5. Expected: No errors (or only warnings)

### Step 2: Test JavaScript Execution
1. In Console tab, type:
   ```javascript
   document.getElementById('observedSD')
   ```
2. Press Enter
3. Expected output: Should show the HTML element (not null)

### Step 3: Verify Values Update
1. Take 10 samples (click "Generate Sample" 10 times)
2. Open Console
3. Type:
   ```javascript
   document.getElementById('observedSD').textContent
   ```
4. Expected: Should show a number like "2.134" (not "—")

### Step 4: Check CLT Box Visibility
1. In Console, type:
   ```javascript
   document.getElementById('cltInfo').style.display
   ```
2. After 5+ samples, should return: "block"
3. Before 5 samples, should return: "none"

## Manual Fix (If All Else Fails)

### Option 1: Force Reload Static Files
```bash
# In terminal, from project root
python manage.py collectstatic --clear --noinput
```

### Option 2: Private/Incognito Window
1. Open browser in Private/Incognito mode
2. Navigate to http://127.0.0.1:8000/stats-simulator/
3. Test functionality
4. If it works here → cache issue confirmed

### Option 3: Different Browser
1. Try in a different browser (Chrome, Firefox, Safari, Edge)
2. If works in other browser → cache/extension issue in original browser

## Debug Mode: Console Logging

If issue persists, add debug logging to `simulator.js`:

**After line 267** (in drawSamplingDistribution function), add:
```javascript
console.log('CLT Info Update:', {
    observedSD: stats.sd.toFixed(3),
    theoreticalSE: theoreticalSE.toFixed(3),
    formula: `σ/√n = ${state.sd}/√${state.sampleSize}`,
    sampleCount: state.sampleMeans.length
});
```

Then:
1. Reload page (hard refresh)
2. Take 10 samples
3. Check Console for debug output
4. Should show values being calculated

## Expected Behavior

### After Taking 5 Samples:
✅ Green CLT box appears below Graph 3
✅ "Observed SD of Sample Means" shows a number (e.g., 2.134)
✅ "Standard Error Formula" shows: SE = σ/√n
✅ "SE Calculation" shows: 5/√5 = 2.236

### Example Output:
```
Observed SD of Sample Means: 2.187
Standard Error Formula: SE = σ/√n
SE Calculation: 5/√5 = 2.236
```

## Still Not Working?

### Check File Contents
Verify the latest code is present:

```bash
# Check if JavaScript has the update
grep -A 5 "Observed SD of sample means" stats_simulator/static/stats_simulator/simulator.js

# Should show:
# document.getElementById('observedSD').textContent = stats.sd.toFixed(3);
```

### Restart Django Server
Sometimes Django needs a restart to pick up static file changes:

```bash
# Stop server (Ctrl+C)
# Then restart:
python manage.py runserver
```

### Check Django Settings
Ensure static files configured correctly in `settings.py`:

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
```

## Success Indicators

✅ **Working correctly when:**
1. CLT box shows actual numbers (not dashes)
2. Observed SD changes with each sample
3. SE Calculation matches σ/√n formula
4. Values update in real-time
5. No console errors

## Contact Support

If none of these solutions work:
1. Take screenshot of browser Console (F12 → Console tab)
2. Note browser name and version
3. Note any error messages
4. Include screenshot showing the issue
5. Report via GitHub issues or contact admin

## Quick Reference: Browser DevTools

| Action | Windows/Linux | Mac |
|--------|--------------|-----|
| Open DevTools | F12 or Ctrl+Shift+I | Cmd+Option+I |
| Hard Refresh | Ctrl+Shift+R | Cmd+Shift+R |
| Clear Cache | Ctrl+Shift+Del | Cmd+Shift+Del |

## Version History

- **v2.0** (Current): Added SE calculation display
- **v1.0**: Initial release with basic CLT info

## Related Files

- `stats_simulator/static/stats_simulator/simulator.js` (lines 257-272)
- `stats_simulator/templates/stats_simulator/index.html` (lines 117-141)
- `stats_simulator/static/stats_simulator/styles.css` (lines 277-358)
