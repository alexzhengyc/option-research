'use client'

import { useState } from 'react'
import { StatsCards } from '@/components/stats-cards'
import {
  DirectionalScoreTimeSeriesChart,
  EWMAScoreTimeSeriesChart,
  SymbolComparisonChart
} from '@/components/signals-chart'
import { SignalsTable } from '@/components/signals-table'
import { useIntradaySignals, useTradeDates } from '@/hooks/useIntradaySignals'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { format } from 'date-fns'

export default function Dashboard() {
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined)
  const { signals, loading, error } = useIntradaySignals(selectedDate)
  const { dates, loading: datesLoading } = useTradeDates()

  return (
    <div className="flex min-h-screen flex-col">
      <div className="border-b">
        <div className="flex h-16 items-center px-8">
          <h1 className="text-3xl font-bold tracking-tight">Intraday Dashboard</h1>
        </div>
      </div>

      <div className="flex-1 space-y-4 p-8 pt-6">
        <div className="flex items-center justify-between space-y-2">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Overview</h2>
            <p className="text-muted-foreground">
              Real-time intraday trading signals and analysis
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Select
              value={selectedDate || 'all'}
              onValueChange={(value) => setSelectedDate(value === 'all' ? undefined : value)}
              disabled={datesLoading}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select date" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Dates</SelectItem>
                {dates.map((date) => (
                  <SelectItem key={date} value={date}>
                    {format(new Date(date), 'MMM dd, yyyy')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardHeader>
              <CardTitle className="text-red-800">Error</CardTitle>
              <CardDescription className="text-red-600">{error}</CardDescription>
            </CardHeader>
          </Card>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-lg text-muted-foreground">Loading signals...</div>
          </div>
        ) : (
          <>
            <StatsCards />

            <Tabs defaultValue="charts" className="space-y-4">
              <TabsList>
                <TabsTrigger value="charts">Charts</TabsTrigger>
                <TabsTrigger value="table">Table View</TabsTrigger>
              </TabsList>

              <TabsContent value="charts" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-1">
                  <DirectionalScoreTimeSeriesChart signals={signals} />
                </div>
                <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-1">
                  <EWMAScoreTimeSeriesChart signals={signals} />
                </div>
                <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-1">
                  <SymbolComparisonChart signals={signals} />
                </div>
              </TabsContent>

              <TabsContent value="table" className="space-y-4">
                <SignalsTable signals={signals} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>
    </div>
  )
}
