# greeks.py
# Calculate option Greeks using mibian
import mibian

def calculate_greeks(underlying_price, strike_price, interest_rate, days_to_expiry, implied_volatility):
    try:
        C = mibian.BS([underlying_price, strike_price, interest_rate, days_to_expiry], implied_volatility)
        return {
            'delta': C.delta,
            'gamma': C.gamma,
            'theta': C.theta,
            'vega': C.vega
        }
    except Exception as e:
        return {
            'delta': None,
            'gamma': None,
            'theta': None,
            'vega': None
        }
