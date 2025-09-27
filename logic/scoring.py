# scoring.py
# Sub-scores & composite scoring logic for signals

def technical_score(ma_alignment, rsi, macd, vol_ratio):
    # Example: 20>50>200 bonus, 20<50<200 penalty, RSI zone, MACD up, VolumeRatio bonus
    score = 0
    if ma_alignment == 'bullish':
        score += 20
    elif ma_alignment == 'bearish':
        score -= 20
    score += min(max((rsi-50)/2, 0), 15)  # RSI zone
    if macd == 'up':
        score += 10
    if vol_ratio >= 1.5:
        score += 15
    return max(score, 0)

def greeks_score(delta, theta, gamma, iv_wow, bid_ask):
    score = 0
    if 0.45 <= delta <= 0.60:
        score += 20
    elif delta < 0.35 or delta > 0.70:
        score -= 10
    score += max(10 + theta, 0)  # Closer to 0 is better
    if gamma > 0:
        score += 5
    if iv_wow >= 0.10:
        score += 10
    if bid_ask > 0.10:
        score -= 10
    return max(score, 0)

def sentiment_score(vix, put_call, fg, macro_risk):
    # Weighted: VIX 30%, Put/Call 30%, F&G 30%, Macro 10%
    score = 0.3*vix + 0.3*put_call + 0.3*fg + 0.1*macro_risk
    return int(score)

def dte_score(dte):
    # Linear penalty as DTE approaches 0; steeper <7
    if dte < 7:
        return -20
    return int(10 * dte / 30)

def composite_score(tech, greeks, sentiment, dte):
    # Weights: Technicals 35%, Greeks 35%, Sentiment 20%, DTE 10%
    return int(0.35*tech + 0.35*greeks + 0.2*sentiment + 0.1*dte)

def signal_from_score(score, theta, dte):
    # Map to signals
    if score >= 75:
        sig = 'BUY'
    elif score >= 60:
        sig = 'HOLD'
    elif score >= 45:
        sig = 'WATCH'
    else:
        sig = 'SELL'
    # ROLL rule
    if score >= 60 and (theta < -0.15 or dte < 7):
        sig += ' + ROLL'
    return sig
