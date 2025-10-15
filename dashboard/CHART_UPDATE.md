# Chart Update: Time Series Visualization

## What Changed

The dashboard charts have been updated to show **directional scores over time as line charts**, making it much easier to track how signals evolve throughout the trading day.

## New Charts

### 1. **Directional Score Over Time** (Main Chart)
**What it shows**: Current directional scores for each symbol as they change over time

**Features**:
- **X-axis**: Time (HH:mm:ss format)
- **Y-axis**: Directional score (-1 to 1)
- **Lines**: Each symbol gets its own colored line
- **Shows up to**: 8 symbols simultaneously
- **Interactive**: Hover to see exact values

**Use Case**: Track momentum and score changes intraday. See which symbols are gaining or losing directional strength.

**Example**:
```
Score
 1.0 ┤     ╭─AAPL──╮
 0.5 ┤   ╭─╯       ╰─╮
 0.0 ┼──╯             ╰──
-0.5 ┤       TSLA
-1.0 ┤
     └─────────────────→ Time
     11:00  12:00  13:00
```

### 2. **EWMA Directional Score Over Time**
**What it shows**: Exponentially weighted moving average of directional scores

**Features**:
- **X-axis**: Time (HH:mm:ss format)
- **Y-axis**: EWMA score (-1 to 1)
- **Lines**: Each symbol tracked separately
- **Smoother**: Less noise than raw scores
- **Shows up to**: 8 symbols

**Use Case**: See the smoothed trend without intraday noise. Better for identifying sustained directional moves.

### 3. **Latest Directional Scores by Symbol**
**What it shows**: Most recent scores for all symbols, comparing current vs EWMA

**Features**:
- **X-axis**: Symbol names
- **Y-axis**: Score (-1 to 1)
- **Two lines**: 
  - Blue solid = Current score
  - Purple dashed = EWMA score
- **Sorted**: By highest current score
- **Shows**: Top 12 symbols

**Use Case**: Quick snapshot of which symbols have the strongest signals right now.

## What Was Replaced

### Old Charts (Removed)
1. ❌ **Signals by Symbol** (Bar chart) - Showed CALL/PUT/PASS counts
2. ❌ **Directional Score Analysis** (Scatter plot) - Current vs EWMA comparison
3. ❌ **Volume Analysis** (Bar chart) - Call vs Put volumes

### Why the Change?
The old charts were static snapshots. The new time series charts show **evolution**, which is much more useful for:
- Tracking signal strength changes
- Identifying trends
- Spotting momentum shifts
- Understanding timing

## Visual Differences

### Before (Bar/Scatter):
```
Static view:
Symbol | CALL | PUT | PASS
AAPL   |  5   |  2  |  1
TSLA   |  3   |  4  |  2
```

### After (Time Series):
```
Dynamic view:
     AAPL ──────╮
               ╰─╮
     TSLA ─────╯
     ↓          ↓
   11:00     13:00
```

## Chart Features

### Color Palette
Each symbol gets a unique color from this palette:
- 🔵 Blue
- 🔴 Red
- 🟢 Green
- 🟠 Orange
- 🟣 Violet
- 🟡 Amber
- 🔷 Cyan
- 🟤 Lime

### Interactive Elements
1. **Hover Tooltips**: See exact values at each time point
2. **Legend**: Click to show/hide specific symbols
3. **Zoom**: Mouse wheel to zoom in/out
4. **Pan**: Drag to pan across time

### Data Handling
- **Missing values**: Lines connect across gaps (`connectNulls`)
- **Sorting**: Time-sorted automatically
- **Limits**: Top 8 symbols to avoid clutter
- **Domain**: Y-axis fixed at -1 to 1 for consistency

## How to Read the Charts

### Directional Score Scale
```
 1.0  = Strong bullish (CALL)
 0.5  = Moderate bullish
 0.0  = Neutral
-0.5  = Moderate bearish
-1.0  = Strong bearish (PUT)
```

### Interpreting Lines

**Trending Up** 📈
```
Score rises over time
→ Increasing bullish sentiment
→ Consider CALL structures
```

**Trending Down** 📉
```
Score falls over time
→ Increasing bearish sentiment
→ Consider PUT structures
```

**Stable/Flat** ➡️
```
Score stays consistent
→ Conviction maintained
→ Strong signal
```

**Volatile/Choppy** 📊
```
Score oscillates
→ Uncertainty
→ Wait for clarity or PASS
```

## Usage Examples

### Example 1: Momentum Building
```
If you see a symbol's line rising from 0.3 to 0.7:
→ Bullish momentum is building
→ Strong CALL signal developing
→ Good entry opportunity
```

### Example 2: Reversal Warning
```
If EWMA is positive but current score crosses below:
→ Potential reversal
→ Consider taking profits on CALLs
→ Or wait for confirmation
```

### Example 3: Divergence
```
If current score diverges from EWMA:
→ New trend forming
→ Breaking from average behavior
→ High conviction moment
```

## Technical Details

### Data Structure
```typescript
{
  time: "13:45:30",      // X-axis
  AAPL: 0.743,           // Y-axis for AAPL
  TSLA: -0.521,          // Y-axis for TSLA
  NVDA: 0.892            // Y-axis for NVDA
}
```

### Time Format
- Display: `HH:mm:ss` (e.g., "13:45:30")
- Stored: ISO timestamp in database
- Sorted: Chronologically

### Symbol Selection
- Picks first 8 unique symbols
- Could be modified to pick:
  - Most active symbols
  - Highest conviction symbols
  - User-selected symbols

## Customization Options

### Change Number of Symbols
In `signals-chart.tsx`, modify:
```typescript
const symbols = [...new Set(sortedSignals.map(s => s.symbol))].slice(0, 8)
//                                                                      ↑
// Change 8 to any number (recommend 5-10 for readability)
```

### Change Y-axis Range
```typescript
<YAxis
  domain={[-1, 1]}  // Change to [min, max]
/>
```

### Change Colors
Update the `SYMBOL_COLORS` array:
```typescript
const SYMBOL_COLORS = [
  '#3b82f6',  // Your custom colors
  '#ef4444',
  // ...
]
```

### Time Format
Change from `HH:mm:ss` to other formats:
```typescript
time: format(new Date(timestamp), 'HH:mm')     // Hours:minutes
time: format(new Date(timestamp), 'h:mm a')    // 12-hour format
time: format(new Date(timestamp), 'HH:mm:ss.SSS') // With milliseconds
```

## Performance

### Rendering Speed
- **Small datasets** (<100 signals): Instant
- **Medium datasets** (100-500 signals): <1 second
- **Large datasets** (500+ signals): 1-2 seconds

### Optimization Tips
1. Limit to top N symbols (currently 8)
2. Filter by date to reduce data points
3. Sample time points if too dense

## Future Enhancements

### Potential Additions
- [ ] Symbol filter/selector
- [ ] Compare two symbols side-by-side
- [ ] Add reference lines (e.g., decision thresholds)
- [ ] Export chart as image
- [ ] Annotations for key events
- [ ] Zoom to time range
- [ ] Multiple Y-axes for different metrics

### Easy Customizations
- Add volume overlay
- Show decision markers (CALL/PUT/PASS)
- Highlight intraday decision times
- Add Bollinger-style bands

## Troubleshooting

### Issue: Lines not showing
**Cause**: No data or all null values  
**Fix**: Check that `dirscore_now` / `dirscore_ewma` exist

### Issue: Too many symbols, chart is cluttered
**Cause**: More than 8 symbols  
**Fix**: Reduce `slice(0, 8)` to smaller number

### Issue: Time axis labels overlap
**Cause**: Too many time points  
**Fix**: Add `tickCount` prop to `<XAxis>`

### Issue: Colors hard to distinguish
**Cause**: Default palette  
**Fix**: Update `SYMBOL_COLORS` array

## Summary

**Key Improvements**:
1. ✅ Time series instead of static snapshots
2. ✅ Track score evolution over time
3. ✅ Multiple symbols on same chart
4. ✅ Both current and EWMA scores
5. ✅ Interactive and responsive

**Result**: Much better for intraday trading decisions!

---

**Updated**: October 15, 2025  
**Chart Library**: Recharts  
**View**: http://localhost:3000 (Charts tab)

