'use client'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { IntradaySignal } from '@/types/supabase'
import { format } from 'date-fns'

interface SignalsTableProps {
  signals: IntradaySignal[]
}

export function SignalsTable({ signals }: SignalsTableProps) {
  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'CALL':
        return <Badge className="bg-green-600 hover:bg-green-700">CALL</Badge>
      case 'PUT':
        return <Badge className="bg-red-600 hover:bg-red-700">PUT</Badge>
      default:
        return <Badge variant="secondary">PASS</Badge>
    }
  }

  const getStructureBadge = (structure: string) => {
    switch (structure) {
      case 'NAKED':
        return <Badge variant="outline">NAKED</Badge>
      case 'VERTICAL':
        return <Badge variant="outline">VERTICAL</Badge>
      default:
        return <Badge variant="outline">SKIP</Badge>
    }
  }

  const formatNumber = (num: number | null, decimals = 2) => {
    if (num === null) return 'N/A'
    return num.toFixed(decimals)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Intraday Signals</CardTitle>
        <CardDescription>
          Detailed view of all intraday trading signals
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Trade Date</TableHead>
                <TableHead>As Of</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Structure</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead className="text-right">Spot Price</TableHead>
                <TableHead className="text-right">Dir Score Now</TableHead>
                <TableHead className="text-right">Dir Score EWMA</TableHead>
                <TableHead className="text-right">RR 25D</TableHead>
                <TableHead className="text-right">Net Thrust</TableHead>
                <TableHead className="text-right">Vol PCR</TableHead>
                <TableHead className="text-right">IV Bump %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {signals.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={13} className="text-center text-muted-foreground">
                    No signals found
                  </TableCell>
                </TableRow>
              ) : (
                signals.map((signal, index) => (
                  <TableRow key={`${signal.asof_ts}-${signal.symbol}-${index}`}>
                    <TableCell className="font-medium">{signal.symbol}</TableCell>
                    <TableCell>{format(new Date(signal.trade_date), 'MMM dd, yyyy')}</TableCell>
                    <TableCell className="text-xs">
                      {format(new Date(signal.asof_ts), 'HH:mm:ss')}
                    </TableCell>
                    <TableCell>{getDecisionBadge(signal.decision)}</TableCell>
                    <TableCell>{getStructureBadge(signal.structure)}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {signal.direction}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      ${formatNumber(signal.spot_price)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(signal.dirscore_now, 3)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(signal.dirscore_ewma, 3)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(signal.rr_25d, 4)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(signal.net_thrust, 2)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(signal.vol_pcr, 2)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(signal.pct_iv_bump, 2)}%
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}

