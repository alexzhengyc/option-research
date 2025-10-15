# Intraday Dashboard

A Next.js dashboard for visualizing intraday trading signals from the option research system.

## Features

- 📊 **Real-time Stats**: View total signals, call/put distribution, and average directional scores
- 📈 **Interactive Charts**: 
  - Signal distribution by symbol
  - Directional score analysis (current vs EWMA)
  - Volume analysis (call vs put)
- 📋 **Data Table**: Detailed view of all signals with filtering
- 🔍 **Date Filtering**: Filter signals by trade date
- 🎨 **Modern UI**: Built with shadcn/ui and Tailwind CSS

## Prerequisites

- Node.js 18+ installed
- Local Supabase instance running (see main project README)
- Intraday signals data in the `eds.intraday_signals` table

## Setup

1. **Copy environment variables**:
   ```bash
   cp .env.example .env.local
   ```

   The default configuration connects to local Supabase:
   ```
   NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open the dashboard**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Usage

### Starting Local Supabase

Before running the dashboard, ensure your local Supabase instance is running:

```bash
# From the main project directory
cd /path/to/option-research
supabase start
```

### Viewing Signals

1. The dashboard automatically loads all signals from the `eds.intraday_signals` table
2. Use the date selector in the top right to filter by specific trade dates
3. Switch between "Charts" and "Table View" tabs to see different visualizations

### Understanding the Metrics

- **Dir Score Now**: Current directional score
- **Dir Score EWMA**: Exponentially weighted moving average of directional score
- **RR 25D**: Risk reversal (25 delta)
- **Net Thrust**: Net thrust indicator
- **Vol PCR**: Volume put/call ratio
- **IV Bump**: Implied volatility bump percentage

## Project Structure

```
dashboard/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main dashboard page
│   └── globals.css         # Global styles
├── components/
│   ├── ui/                 # shadcn/ui components
│   ├── stats-cards.tsx     # Statistics cards
│   ├── signals-chart.tsx   # Chart components
│   └── signals-table.tsx   # Data table component
├── hooks/
│   └── useIntradaySignals.ts  # Data fetching hooks
├── lib/
│   ├── supabase.ts         # Supabase client
│   └── utils.ts            # Utility functions
└── types/
    └── supabase.ts         # TypeScript types
```

## Development

### Adding New Charts

To add a new chart, create a new component in `components/signals-chart.tsx`:

```typescript
export function MyNewChart({ signals }: SignalsChartProps) {
  // Your chart implementation
}
```

Then add it to `app/page.tsx`:

```typescript
import { MyNewChart } from '@/components/signals-chart'

// In your component
<MyNewChart signals={signals} />
```

### Customizing the Theme

The dashboard uses shadcn/ui with Tailwind CSS v4. To customize colors and styling:

1. Edit `app/globals.css` to change CSS variables
2. Modify component styles in individual component files

## Troubleshooting

### "Error fetching signals"

- Ensure Supabase is running: `supabase status`
- Check that the `eds.intraday_signals` table exists
- Verify the connection URL in `.env.local`

### No data showing

- Run the intraday pipeline to generate signals:
  ```bash
  cd /path/to/option-research
  python jobs/intraday.py
  ```
- Check that signals exist in the database:
  ```sql
  SELECT COUNT(*) FROM eds.intraday_signals;
  ```

### Port already in use

If port 3000 is already in use, you can specify a different port:

```bash
npm run dev -- -p 3001
```

## Technologies Used

- **Next.js 15**: React framework with App Router
- **TypeScript**: Type safety
- **shadcn/ui**: Beautiful, accessible UI components
- **Tailwind CSS v4**: Utility-first CSS framework
- **Recharts**: Charting library
- **Supabase**: Database and real-time subscriptions
- **date-fns**: Date formatting utilities

## License

MIT
