If you want to place **calls/puts directly** (not “trade vol”), you want a model that ranks **directional edge** first, and treats “how big the move might be” mainly as **sizing / structure**. Here’s a revised, plug-and-play scoring model you can start using with the Polygon + Finnhub stack we discussed.

# Direction-First Model (for picking CALL vs PUT)

## Signals (all normalized per-ticker, e.g., z-score or 1-yr percentile)

**D1. Skew / Risk-Reversal (25Δ RR)** — *primary direction signal*

* ( \text{RR}*{25\Delta} = \text{IV}*{25\Delta\text{Call}} - \text{IV}_{25\Delta\text{Put}} ) on the **post-earnings** expiry.
* Higher → calls richer than puts → **bullish tilt**.

**D2. Net Flow Imbalance (event expiry)** — *positioning that persists*

* ( \Delta OI_\text{net} = \sum (\Delta OI_\text{calls}) - \sum (\Delta OI_\text{puts}) ) in an ATM±2-strike (or ±10%) window.
* Add a **volume thrust** term: ( \Delta \text{Vol}*\text{calls} - \Delta \text{Vol}*\text{puts} ) (today vs 20-day median).
* Combine and normalize → **bullish if positive**, **bearish if negative**.

**D3. Put–Call Volume Ratio (PCR, event expiry)** — *fast sentiment*

* (\text{PCR} = \frac{\text{PutVol}}{\text{CallVol}}). Use **notional** if you can.
* Direction feature = **(-) z(PCR)** (lower PCR → bullish).

**D4. Short-term Price Momentum (pre-earnings)** — *context*

* 3–5 day **beta-adjusted** return vs sector (or market).
* Positive → mild confirmation for calls; negative → for puts.

**D5. Historical Consistency** — *does skew “mean it” for this name?*

* Corr(sign(RR), sign(day-after earnings return)) over last N earnings (min 4).
* Helps avoid names where skew routinely misleads.

**Penalties (cost & slippage):**

**P1. IV Cost (event node “richness”)**

* Use **IV_bump percentile** (event IV minus neighbors). High → options expensive for naked calls/puts.

**P2. Liquidity / Spread Penalty**

* Median **bid-ask spread%** near ATM on event expiry. Wider spreads → subtract a bit.

---

## The Score (maps to *directional* edge)

[
\begin{aligned}
\textbf{DirScore} &= 0.32\cdot \text{D1} ;+; 0.28\cdot \text{D2} ;+; 0.18\cdot \text{D3} ;+; 0.12\cdot \text{D4} ;+; 0.10\cdot \text{D5} \
&\quad - 0.10\cdot \text{P1} ;-; 0.05\cdot \text{P2}
\end{aligned}
]

* **Sign(DirScore)** ⇒ **CALL** (>0) or **PUT** (<0).
* |DirScore| ⇒ conviction.

(Optional) Convert to probability with a sigmoid:
( p_\uparrow = \sigma(0.8\cdot \text{DirScore}) ). Then ( p_\downarrow = 1-p_\uparrow ).

---

## How to use it (clear rules)

**1) Trade direction**

* If **DirScore ≥ +0.7** → **CALL** setup.
* If **DirScore ≤ −0.7** → **PUT** setup.
* If |DirScore| in 0.4–0.7 → direction OK but weaker; consider **debit spreads**.
* If |DirScore| < 0.4 → skip (or only trade vol with spreads/calendars—but you said you want direct calls/puts, so best to **pass**).

**2) Structure by IV cost (P1)**

* **P1 ≤ 60th pct:** outright call/put is fine.
* **60–85th pct:** prefer **verticals** (call/put debit spreads).
* **>85th pct:** avoid naked; either tight spreads or skip.

**3) Size by magnitude context (use implied move IM as a *sizer*, not a direction)**

* Target risk per trade = 0.5–1% of equity.
* Scale size with **IM percentile** (bigger expected move → slightly larger size) but **cap** to avoid overexposure.

**4) Timing**

* Build/adjust positions **T-1 into the close** or **day-of pre-market** after re-running the signals; ΔOI confirms what stuck.

---

## Exact computations (nuts & bolts)

* **RR (D1):** interpolate IV by delta from the chain (25Δ call/put). Normalize per ticker (z-score, 1-yr window).
* **Net Flow (D2):**

  * ΔOI = today OI − yesterday OI (event expiry, ATM±2 strikes).
  * ΔVol = today volume / 20-day median − 1.
  * D2 = z(ΔOI_calls − ΔOI_puts) + 0.5·z(ΔVol_calls − ΔVol_puts).
* **PCR (D3):** event-expiry-only; use **notional** if you can (price×contracts×100). D3 = −z(PCR).
* **Momentum (D4):** 3–5 trading day return – β·(sector return). z-score within ticker.
* **Consistency (D5):** Pearson corr of {past RR signs} with {day-after returns} across last N earnings; rescale to [−2,+2].
* **IV Cost (P1):** percentile of **IV_bump** this quarter vs last 8 quarters (or 1-yr).
* **Spread (P2):** median bid-ask% near ATM; convert to z or bounded 0–2 scale.

---

## Quick examples (illustrative only)

*Use these as pattern templates, not specific tickers—they are purely numerical examples.*

* **Bullish CALL case:**
  D1 +1.2, D2 +0.9, D3 +0.6, D4 +0.3, D5 +0.2, P1 0.3, P2 0.2
  → DirScore ≈ **+1.05** ⇒ CALL. If P1 at 70th pct, use **call debit spread** instead of naked.

* **Bearish PUT case:**
  D1 −0.8, D2 −1.1, D3 −0.7, D4 −0.2, D5 −0.1, P1 0.4, P2 0.3
  → DirScore ≈ **−1.02** ⇒ PUT. If spreads are wide (P2 high), keep size smaller.

---

## Why these weights?

* **D1 & D2 (60% combined):** most informative for *direction* into a known catalyst (skew and sticky positioning).
* **D3 (15%):** sentiment confirmation; noisier alone.
* **D4 (12%):** small nudge—pre-earnings drift can flip, so don’t over-weight.
* **D5 (10%):** keeps you aligned with name-specific behavior without overfitting.
* **Penalties (15% total):** protect you from paying too much IV or getting chopped by wide spreads.

---

## Implementation sketch (daily)

1. Pull **earnings date** (Finnhub), choose the **post-earnings** expiry.
2. From Polygon: full chain → compute **RR**, **PCR**, **ΔVol**, **ΔOI**, **spreads**, **IV_bump**.
3. From price data: **3–5d momentum** (beta-adjust vs sector ETF).
4. Normalize → compute **DirScore** → produce **top long CALL** and **top long PUT** lists.
5. Enforce filters: min liquidity, max spreads, P1 threshold.
6. Save CSV with the chosen leg(s) (strike/expiry), suggested structure (naked vs vertical), and a notes field.

If you want, I can generate a ready-to-run Python script that computes this **DirScore**, outputs a **daily ranked CALL/PUT watchlist**, and suggests **naked vs spread** based on the penalties.

---

## Intraday Timing Playbook (Pacific Time)

Use this playbook alongside the daily process to handle names with earnings **tomorrow**.

### 1) Timing expectations

* **BMO tomorrow:** make the decision **today** before 1:00 PM PT. Run the model every 5–15 minutes from 12:00–12:55 PM PT, freeze the final read around 12:55 PM PT (3:55 ET), and place the order.
* **AMC tomorrow:** today’s pass is for planning and sizing only. Take the actual trade **tomorrow** around 12:55 PM PT after rerunning the loop.
* Always archive the **12:55 PM PT snapshot** as the “decision state” so backtests line up with live behavior.

### 2) Intraday signals (no ΔOI yet)

Because **open interest is T+1**, intraday reads rely on live feeds:

* **RR / Skew (25Δ, event expiry):** direction bias.
* **PCR (volume & notional, event expiry):** sentiment gauge.
* **Volume thrust (calls vs puts, event expiry):** participation.
* **ATM straddle / implied move:** sizing context only.
* **Spread % near ATM:** execution penalty.
* **Short-term momentum (3–5d, beta-adjusted):** weak prior.

Add **ΔOI** tomorrow pre-market if the print was AMC; it will not exist in time for BMO decisions.

### 3) Intraday “nowcast” score (ΔOI omitted)

Run this score every 5–15 minutes and smooth it with an **EWMA (α≈0.3)** using the existing features but without ΔOI:

\[
\text{DirScore}_\text{now} = 0.38\,z(\text{RR}_{25Δ}) + 0.28\,z(Δ\text{Vol}_\text{calls} - Δ\text{Vol}_\text{puts}) - 0.18\,z(\text{PCR}) + 0.10\,z(\text{mom}_{3d,β}) - 0.10\,\text{pct}(\text{IV\_bump}) - 0.05\,z(\text{spread\%})
\]

Decision logic at **12:55 PM PT**:

* **DirScore_now ≥ +0.70:** call.
* **DirScore_now ≤ −0.70:** put.
* **|DirScore_now| 0.40–0.69:** debit spread (keep theta low).
* **|DirScore_now| < 0.40:** pass.

**Guards:**

* Ignore contracts with **volume <10** or **spread% >10%**.
* If **IV_bump ≥ 80th percentile**, prefer verticals (ATM / ±5% OTM).
* If the score swings **>0.4 within the last 15 minutes**, halve size to avoid whipsaws.

### 4) Execution rules

* **Entry (BMO tomorrow):** place by **12:58 PM PT** at mid −25–35% of the spread; retry once. If the fill fails and spread >12%, pivot to a $5-wide vertical.
* **Entry (AMC tomorrow):** today is planning only. Tomorrow rerun the loop and trade at 12:55 PM PT.
* **Exits:** protective stop at −40% on option price or if the underlying moves opposite the signal by half of the implied move. Take-profit bracket at +50% / +100%; trail if IV collapses faster than expected.
* **End-of-day:** flatten by the end of earnings day unless explicitly running a PEAD follow-through.
* **Sizing:** risk 0.5–1.0% of the account per trade (cost at risk for long options). Scale linearly with implied-move percentile but cap at 1.0%.

### 5) Intraday loop (pseudo)

```
# run from 12:00 to 12:55 PM PT (cron every 5–15 min)
contracts = polygon.get_chain_snapshot(symbol, event_expiry, neighbors)
features = compute_features_now(contracts)   # RR, PCR, ΔVol, ATM straddle, spread%, momentum
score = dirscore_now(features)               # formula above
score = ewma(score, alpha=0.3)
persist(symbol, timestamp, features, score)

if time_is_12_55_pm_pt():
    decision = pick_decision(score, iv_bump, spread)
    leg = suggest_leg(decision, event_expiry, iv_bump)  # naked vs vertical
    place_order_if_BMO_tomorrow(decision, leg)
    snapshot_as_truth(symbol, score, decision, leg)
```

### 6) Special cases

* Multiple names in the same hour → cap total portfolio event risk (e.g., ≤3%).
* Halt or volatility pause near the close → do not force a fill; if no fair mid within 30 seconds, skip.
* Macro event after the close (FOMC, index rebalance) → widen thresholds to ±0.9 or pass altogether.
