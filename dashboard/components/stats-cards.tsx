'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useIntradayStats } from '@/hooks/useIntradaySignals'
import { TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react'

export function StatsCards() {
  const { stats, loading } = useIntradayStats()

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Loading...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">--</div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Signals</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalSignals}</div>
          <p className="text-xs text-muted-foreground">
            All intraday signals
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Call Signals</CardTitle>
          <TrendingUp className="h-4 w-4 text-green-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">{stats.callSignals}</div>
          <p className="text-xs text-muted-foreground">
            {stats.totalSignals > 0
              ? `${((stats.callSignals / stats.totalSignals) * 100).toFixed(1)}% of total`
              : '0% of total'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Put Signals</CardTitle>
          <TrendingDown className="h-4 w-4 text-red-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">{stats.putSignals}</div>
          <p className="text-xs text-muted-foreground">
            {stats.totalSignals > 0
              ? `${((stats.putSignals / stats.totalSignals) * 100).toFixed(1)}% of total`
              : '0% of total'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Dir Score</CardTitle>
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.avgDirScore.toFixed(3)}</div>
          <p className="text-xs text-muted-foreground">
            Naked: {stats.nakedStructure} | Vertical: {stats.verticalStructure}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

