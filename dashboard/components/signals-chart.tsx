'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { IntradaySignal } from '@/types/supabase'
import { format } from 'date-fns'
import {
  Line,
  LineChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'

interface SignalsChartProps {
  signals: IntradaySignal[]
}

// Color palette for different symbols
const SYMBOL_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
  '#a855f7', // purple
]

export function DirectionalScoreTimeSeriesChart({ signals }: SignalsChartProps) {
  // Sort signals by time
  const sortedSignals = [...signals].sort((a, b) => 
    new Date(a.asof_ts).getTime() - new Date(b.asof_ts).getTime()
  )

  // Get top 7 symbols by highest absolute directional score (highest conviction)
  const latestBySymbol = signals.reduce((acc, signal) => {
    const existing = acc[signal.symbol]
    if (!existing || new Date(signal.asof_ts) > new Date(existing.asof_ts)) {
      acc[signal.symbol] = signal
    }
    return acc
  }, {} as Record<string, IntradaySignal>)

  const symbols = Object.values(latestBySymbol)
    .sort((a, b) => Math.abs(b.dirscore_now || 0) - Math.abs(a.dirscore_now || 0))
    .slice(0, 7)
    .map(s => s.symbol)

  // Prepare data for line chart - one point per timestamp
  const timePoints = [...new Set(sortedSignals.map(s => s.asof_ts))]
  
  const chartData = timePoints.map(timestamp => {
    const dataPoint: any = {
      timestamp,
      time: format(new Date(timestamp), 'HH:mm:ss')
    }
    
    // Add score for each symbol at this timestamp
    symbols.forEach(symbol => {
      const signal = sortedSignals.find(s => s.asof_ts === timestamp && s.symbol === symbol)
      dataPoint[symbol] = signal?.dirscore_now
    })
    
    return dataPoint
  })

  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>Directional Score Over Time</CardTitle>
        <CardDescription>
          Top 7 tickers by highest conviction (absolute directional score)
        </CardDescription>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[-1, 1]}
              label={{ value: 'Dir Score', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }}
              labelFormatter={(value) => `Time: ${value}`}
            />
            <Legend />
            {symbols.map((symbol, index) => (
              <Line
                key={symbol}
                type="monotone"
                dataKey={symbol}
                stroke={SYMBOL_COLORS[index % SYMBOL_COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name={symbol}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

export function EWMAScoreTimeSeriesChart({ signals }: SignalsChartProps) {
  // Sort signals by time
  const sortedSignals = [...signals].sort((a, b) => 
    new Date(a.asof_ts).getTime() - new Date(b.asof_ts).getTime()
  )

  // Get top 7 symbols by highest absolute directional score
  const latestBySymbol = signals.reduce((acc, signal) => {
    const existing = acc[signal.symbol]
    if (!existing || new Date(signal.asof_ts) > new Date(existing.asof_ts)) {
      acc[signal.symbol] = signal
    }
    return acc
  }, {} as Record<string, IntradaySignal>)

  const symbols = Object.values(latestBySymbol)
    .sort((a, b) => Math.abs(b.dirscore_now || 0) - Math.abs(a.dirscore_now || 0))
    .slice(0, 7)
    .map(s => s.symbol)

  // Prepare data for line chart
  const timePoints = [...new Set(sortedSignals.map(s => s.asof_ts))]
  
  const chartData = timePoints.map(timestamp => {
    const dataPoint: any = {
      timestamp,
      time: format(new Date(timestamp), 'HH:mm:ss')
    }
    
    // Add EWMA score for each symbol at this timestamp
    symbols.forEach(symbol => {
      const signal = sortedSignals.find(s => s.asof_ts === timestamp && s.symbol === symbol)
      dataPoint[symbol] = signal?.dirscore_ewma
    })
    
    return dataPoint
  })

  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>EWMA Directional Score Over Time</CardTitle>
        <CardDescription>
          Top 7 tickers - smoothed trend without intraday noise
        </CardDescription>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[-1, 1]}
              label={{ value: 'EWMA Score', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }}
              labelFormatter={(value) => `Time: ${value}`}
            />
            <Legend />
            {symbols.map((symbol, index) => (
              <Line
                key={symbol}
                type="monotone"
                dataKey={symbol}
                stroke={SYMBOL_COLORS[index % SYMBOL_COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name={symbol}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

export function SymbolComparisonChart({ signals }: SignalsChartProps) {
  // Get latest directional score for each symbol
  const latestBySymbol = signals.reduce((acc, signal) => {
    const existing = acc[signal.symbol]
    if (!existing || new Date(signal.asof_ts) > new Date(existing.asof_ts)) {
      acc[signal.symbol] = signal
    }
    return acc
  }, {} as Record<string, IntradaySignal>)

  const chartData = Object.values(latestBySymbol)
    .map(s => ({
      symbol: s.symbol,
      score: s.dirscore_now,
      ewma: s.dirscore_ewma,
      decision: s.decision,
      time: format(new Date(s.asof_ts), 'HH:mm')
    }))
    .sort((a, b) => Math.abs(b.score || 0) - Math.abs(a.score || 0))
    .slice(0, 7)

  const getColor = (decision: string) => {
    switch (decision) {
      case 'CALL':
        return '#22c55e'
      case 'PUT':
        return '#ef4444'
      default:
        return '#94a3b8'
    }
  }

  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>Latest Directional Scores by Symbol</CardTitle>
        <CardDescription>
          Top 7 tickers by highest conviction - current vs EWMA comparison
        </CardDescription>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="symbol"
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[-1, 1]}
              label={{ value: 'Dir Score', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }}
              formatter={(value: any, name: string) => {
                if (name === 'score') return [value?.toFixed(3), 'Current Score']
                if (name === 'ewma') return [value?.toFixed(3), 'EWMA Score']
                return [value, name]
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2 }}
              name="Current Score"
            />
            <Line
              type="monotone"
              dataKey="ewma"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2 }}
              strokeDasharray="5 5"
              name="EWMA Score"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

