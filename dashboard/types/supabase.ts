export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      intraday_signals: {
        Row: {
          trade_date: string
          symbol: string
          event_expiry: string | null
          asof_ts: string
          spot_price: number | null
          rr_25d: number | null
          net_thrust: number | null
          vol_pcr: number | null
          beta_adj_return: number | null
          iv_bump: number | null
          spread_pct_atm: number | null
          z_rr_25d: number | null
          z_net_thrust: number | null
          z_vol_pcr: number | null
          z_beta_adj_return: number | null
          pct_iv_bump: number | null
          z_spread_pct_atm: number | null
          dirscore_now: number | null
          dirscore_ewma: number | null
          decision: 'CALL' | 'PUT' | 'PASS'
          structure: 'NAKED' | 'VERTICAL' | 'SKIP'
          direction: 'CALL' | 'PUT' | 'NONE'
          call_volume: number | null
          put_volume: number | null
          total_volume: number | null
          size_reduction: number | null
          notes: string | null
          ewma_alpha: number | null
        }
        Insert: {
          trade_date: string
          symbol: string
          event_expiry?: string | null
          asof_ts: string
          spot_price?: number | null
          rr_25d?: number | null
          net_thrust?: number | null
          vol_pcr?: number | null
          beta_adj_return?: number | null
          iv_bump?: number | null
          spread_pct_atm?: number | null
          z_rr_25d?: number | null
          z_net_thrust?: number | null
          z_vol_pcr?: number | null
          z_beta_adj_return?: number | null
          pct_iv_bump?: number | null
          z_spread_pct_atm?: number | null
          dirscore_now?: number | null
          dirscore_ewma?: number | null
          decision: 'CALL' | 'PUT' | 'PASS'
          structure: 'NAKED' | 'VERTICAL' | 'SKIP'
          direction: 'CALL' | 'PUT' | 'NONE'
          call_volume?: number | null
          put_volume?: number | null
          total_volume?: number | null
          size_reduction?: number | null
          notes?: string | null
          ewma_alpha?: number | null
        }
        Update: {
          trade_date?: string
          symbol?: string
          event_expiry?: string | null
          asof_ts?: string
          spot_price?: number | null
          rr_25d?: number | null
          net_thrust?: number | null
          vol_pcr?: number | null
          beta_adj_return?: number | null
          iv_bump?: number | null
          spread_pct_atm?: number | null
          z_rr_25d?: number | null
          z_net_thrust?: number | null
          z_vol_pcr?: number | null
          z_beta_adj_return?: number | null
          pct_iv_bump?: number | null
          z_spread_pct_atm?: number | null
          dirscore_now?: number | null
          dirscore_ewma?: number | null
          decision?: 'CALL' | 'PUT' | 'PASS'
          structure?: 'NAKED' | 'VERTICAL' | 'SKIP'
          direction?: 'CALL' | 'PUT' | 'NONE'
          call_volume?: number | null
          put_volume?: number | null
          total_volume?: number | null
          size_reduction?: number | null
          notes?: string | null
          ewma_alpha?: number | null
        }
      }
    }
  }
}

export type IntradaySignal = Database['public']['Tables']['intraday_signals']['Row']

