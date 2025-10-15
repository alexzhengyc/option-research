'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { IntradaySignal } from '@/types/supabase'

export function useIntradaySignals(tradeDate?: string) {
  const [signals, setSignals] = useState<IntradaySignal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchSignals() {
      try {
        setLoading(true)
        let query = supabase
          .from('intraday_signals')
          .select('*')
          .order('asof_ts', { ascending: false })

        if (tradeDate) {
          query = query.eq('trade_date', tradeDate)
        }

        const { data, error } = await query

        if (error) throw error
        setSignals(data || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred')
      } finally {
        setLoading(false)
      }
    }

    fetchSignals()
  }, [tradeDate])

  return { signals, loading, error }
}

export function useIntradayStats() {
  const [stats, setStats] = useState({
    totalSignals: 0,
    callSignals: 0,
    putSignals: 0,
    passSignals: 0,
    nakedStructure: 0,
    verticalStructure: 0,
    avgDirScore: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        const { data, error } = await supabase
          .from('intraday_signals')
          .select('*')

        if (error) throw error

        const signals = (data || []) as IntradaySignal[]
        
        const totalSignals = signals.length
        const callSignals = signals.filter(s => s.decision === 'CALL').length
        const putSignals = signals.filter(s => s.decision === 'PUT').length
        const passSignals = signals.filter(s => s.decision === 'PASS').length
        const nakedStructure = signals.filter(s => s.structure === 'NAKED').length
        const verticalStructure = signals.filter(s => s.structure === 'VERTICAL').length
        
        const dirScores = signals
          .map(s => s.dirscore_now)
          .filter((s): s is number => s !== null)
        const avgDirScore = dirScores.length > 0
          ? dirScores.reduce((sum, score) => sum + score, 0) / dirScores.length
          : 0

        setStats({
          totalSignals,
          callSignals,
          putSignals,
          passSignals,
          nakedStructure,
          verticalStructure,
          avgDirScore
        })
      } catch (err) {
        console.error('Error fetching stats:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  return { stats, loading }
}

export function useTradeDates() {
  const [dates, setDates] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchDates() {
      try {
        const { data, error } = await supabase
          .from('intraday_signals')
          .select('trade_date')
          .order('trade_date', { ascending: false })

        if (error) throw error

        const dateData = (data || []) as Array<{ trade_date: string }>
        const uniqueDates = [...new Set(dateData.map(d => d.trade_date))]
        setDates(uniqueDates)
      } catch (err) {
        console.error('Error fetching dates:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchDates()
  }, [])

  return { dates, loading }
}

