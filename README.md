# TradexoAI Signal Bot

Automated crypto signal generator using technical analysis.

## How it works

- Fetches data from Binance (free, no key needed)
- Analyzes 16 top coins every 30 minutes
- Generates LONG/SHORT signals based on:
  - RSI (overbought/oversold)
  - MACD (momentum)
  - EMA 20/50 (trend)
  - Bollinger Bands (volatility)
  - Volume spikes
- Posts signals to Supabase `bot_signals` table
- App automatically displays them

## Setup

1. **GitHub Secrets** (Settings → Secrets and variables → Actions):
- `SUPABASE_URL` = `https://maftyyqruhbaiiafivmh.supabase.co`
- `SUPABASE_SERVICE_KEY` = your service role key
1. **Enable Actions** (Settings → Actions → General → Allow all actions)
1. **Manual run** (Actions tab → Run Signal Bot → Run workflow)

## Schedule

Bot runs every 30 minutes automatically.

## Free tier limits

GitHub Actions free: 2000 minutes/month
Bot uses ~1 minute per run × 48 runs/day = 1440 min/month ✓