# Dashboard Features

## Overview
A comprehensive Next.js dashboard for visualizing intraday trading signals from the option research system, featuring real-time data visualization, interactive charts, and detailed signal analysis.

## Features Implemented

### 1. Statistics Overview Cards
**File**: `components/stats-cards.tsx`

Four key metric cards displaying:
- **Total Signals**: Total count of all intraday signals with activity icon
- **Call Signals**: Number and percentage of call signals (green indicator)
- **Put Signals**: Number and percentage of put signals (red indicator)  
- **Average Directional Score**: Mean score with breakdown of naked vs vertical structures

### 2. Interactive Charts
**File**: `components/signals-chart.tsx`

Three comprehensive chart visualizations:

#### a) Signals by Symbol (Bar Chart)
- Shows distribution of CALL, PUT, and PASS signals across top 10 symbols
- Color-coded bars: Green (CALL), Red (PUT), Gray (PASS)
- Helps identify which symbols generate most signals

#### b) Directional Score Analysis (Scatter Plot)
- Plots current directional score vs EWMA score
- Each point represents a signal, colored by decision type
- Bubble size represents risk reversal (25 delta)
- Helps visualize signal strength and momentum

#### c) Volume Analysis (Bar Chart)
- Compares call volume vs put volume for recent signals
- Shows volume distribution across top 15 signals
- Includes put/call ratio tooltip information

### 3. Detailed Data Table
**File**: `components/signals-table.tsx`

Comprehensive table view featuring:
- **Symbol & Date Information**: Symbol, trade date, timestamp
- **Decision Indicators**: Color-coded badges for CALL (green), PUT (red), PASS (gray)
- **Structure Types**: NAKED, VERTICAL, or SKIP
- **Direction**: CALL, PUT, or NONE
- **Key Metrics**: 
  - Spot price
  - Directional scores (current and EWMA)
  - Risk reversal (25D)
  - Net thrust
  - Volume P/C ratio
  - IV bump percentage

### 4. Data Fetching Hooks
**File**: `hooks/useIntradaySignals.ts`

Three custom React hooks:

#### a) `useIntradaySignals(tradeDate?)`
- Fetches signals from Supabase
- Optional date filtering
- Returns signals, loading state, and error state
- Automatically orders by timestamp (most recent first)

#### b) `useIntradayStats()`
- Aggregates signal statistics
- Calculates counts for each decision type
- Computes average directional score
- Counts structure types

#### c) `useTradeDates()`
- Fetches unique trade dates
- Orders dates newest first
- Enables date picker filtering

### 5. Main Dashboard Page
**File**: `app/page.tsx`

Main dashboard interface featuring:
- **Header**: Clean, professional dashboard header
- **Date Filter**: Dropdown to filter by specific trade dates or view all
- **Tab Navigation**: Switch between "Charts" and "Table View"
- **Error Handling**: Displays errors in user-friendly format
- **Loading States**: Shows loading indicators while fetching data
- **Responsive Layout**: Works on desktop and mobile devices

### 6. Database Integration
**Files**: `lib/supabase.ts`, `types/supabase.ts`

- Configured Supabase client for local instance
- TypeScript types matching database schema
- Type-safe queries and data access
- Schema from `eds.intraday_signals` table

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 15.5.5 | React framework with App Router |
| TypeScript | Latest | Type safety |
| Tailwind CSS | v4 | Styling |
| shadcn/ui | Latest | UI component library |
| Recharts | Latest | Data visualization |
| Supabase | Latest | Database client |
| date-fns | Latest | Date formatting |
| lucide-react | Latest | Icons |

## Key Design Decisions

### 1. Real-time Data
- Direct connection to Supabase enables real-time updates
- Could be extended with subscriptions for live data streaming

### 2. Performance
- Client-side rendering for dynamic data
- Efficient React hooks with proper dependency arrays
- Optimized queries to fetch only needed data

### 3. User Experience
- Clean, minimal interface focusing on data
- Color-coded indicators for quick decision recognition
- Multiple visualization modes (charts vs tables)
- Date filtering for historical analysis

### 4. Maintainability
- Modular component structure
- Reusable hooks for data fetching
- TypeScript for type safety
- Clear separation of concerns

## Future Enhancement Possibilities

### 1. Real-time Updates
```typescript
// Add subscription in useIntradaySignals hook
const subscription = supabase
  .channel('intraday_signals')
  .on('postgres_changes', { event: '*', schema: 'eds', table: 'intraday_signals' }, 
    payload => {
      // Update signals in real-time
    })
  .subscribe()
```

### 2. Advanced Filtering
- Filter by symbol
- Filter by decision type (CALL/PUT/PASS)
- Filter by structure (NAKED/VERTICAL)
- Multi-select date ranges

### 3. Export Functionality
- Export filtered data to CSV
- Generate PDF reports
- Share dashboard snapshots

### 4. Historical Analysis
- Performance tracking over time
- Win/loss tracking
- ROI calculations
- Backtest visualization

### 5. Additional Charts
- Time series of directional scores
- IV surface visualization
- Correlation heatmaps
- Performance attribution

### 6. User Preferences
- Save custom filters
- Customize chart colors
- Set default views
- Dark mode toggle

### 7. Alerts & Notifications
- Desktop notifications for new signals
- Email alerts for high-conviction signals
- Configurable threshold alerts

## API Endpoints Used

The dashboard connects to local Supabase at `http://127.0.0.1:54321`

### Main Query
```typescript
supabase
  .from('intraday_signals')
  .select('*')
  .order('asof_ts', { ascending: false })
  .eq('trade_date', selectedDate) // optional
```

## Responsive Design

The dashboard adapts to different screen sizes:
- **Desktop**: Multi-column layout with full charts
- **Tablet**: Stacked charts with readable tables
- **Mobile**: Single-column view with horizontal scroll for tables

## Accessibility

- Semantic HTML structure
- ARIA labels on interactive elements
- Keyboard navigation support
- Screen reader friendly
- High contrast color scheme

## Testing

To test the dashboard:

1. Ensure Supabase is running and has data:
   ```bash
   supabase status
   ```

2. Run the development server:
   ```bash
   cd dashboard
   npm run dev
   ```

3. Open http://localhost:3000

4. Verify:
   - Stats cards show correct counts
   - Charts render with data
   - Table displays all signals
   - Date filter works correctly
   - No console errors

