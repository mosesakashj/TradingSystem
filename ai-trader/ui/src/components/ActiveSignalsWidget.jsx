import React from 'react'
import { TrendingUp, TrendingDown, Target, Shield, BarChart2, Activity, Zap } from 'lucide-react'

export function ActiveSignalsWidget() {
  // Institutional-grade mock signals
  const activeSignals = [
    {
      id: 1,
      pair: 'EURUSD',
      status: 'ongoing',
      direction: 'buy',
      strategy: 'Smart Money Concept',
      timeframe: 'H4',
      entryPrice: 1.0465,
      currentPrice: 1.0482,
      stopLoss: 1.0435,
      targets: [1.0500, 1.0525, 1.0580], // TP1, TP2, TP3
      winProbability: 78,
      confidence: ['Liquidity Sweep', 'Bullish Order Block', 'RSI Divergence'],
      volatility: 'Medium',
      timestamp: '2h ago'
    },
    {
      id: 2,
      pair: 'GBPUSD',
      status: 'waiting',
      direction: 'sell',
      strategy: 'Trend Continuation',
      timeframe: 'H1',
      entryPrice: 1.2590,
      currentPrice: 1.2580,
      stopLoss: 1.2620,
      targets: [1.2550, 1.2530, 1.2480],
      winProbability: 72,
      confidence: ['EMA Crossover', 'Bearish Flag'],
      volatility: 'High',
      timestamp: '15m ago'
    },
    {
      id: 3,
      pair: 'XAUUSD',
      status: 'succeeded',
      direction: 'buy',
      strategy: 'Safe Haven Flow',
      timeframe: 'D1',
      entryPrice: 4050.00,
      currentPrice: 4065.00,
      stopLoss: 4020.00,
      targets: [4060.00, 4080.00, 4100.00],
      winProbability: 85,
      confidence: ['Global Uncertainty', 'Support Bounce'],
      volatility: 'High',
      timestamp: '4h ago'
    },
    {
      id: 4,
      pair: 'BTCUSD',
      status: 'ongoing',
      direction: 'buy',
      strategy: 'Volume Breakout',
      timeframe: 'M15',
      entryPrice: 84200.00,
      currentPrice: 84599.00,
      stopLoss: 83800.00,
      targets: [84800.00, 85500.00, 86000.00],
      winProbability: 65,
      confidence: ['Volume Spike', 'Triangle Break'],
      volatility: 'Extreme',
      timestamp: '1h ago'
    }
  ]

  const getStatusColor = (status) => {
    switch(status) {
      case 'waiting': return { bg: 'rgba(59, 130, 246, 0.1)', text: '#60a5fa', border: '#3b82f6' }
      case 'ongoing': return { bg: 'rgba(16, 185, 129, 0.1)', text: '#34d399', border: '#10b981' }
      case 'succeeded': return { bg: 'rgba(245, 158, 11, 0.1)', text: '#fbbf24', border: '#f59e0b' }
      default: return { bg: '#374151', text: '#9ca3af', border: '#6b7280' }
    }
  }

  const calculateRR = (signal) => {
    const risk = Math.abs(signal.entryPrice - signal.stopLoss)
    const reward = Math.abs(signal.targets[signal.targets.length - 1] - signal.entryPrice)
    return (reward / risk).toFixed(2)
  }

  const formatPrice = (price, pair) => {
    const decimals = pair.includes('JPY') || pair.includes('XAU') || pair.includes('BTC') ? 2 : 4 // Simplified logic
    return price.toFixed(decimals)
  }

  return (
    <div style={{ padding: '24px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
          <Zap size={20} color="#f59e0b" />
          Institutional Signals
          <span style={{ fontSize: '12px', backgroundColor: '#334155', padding: '2px 8px', borderRadius: '12px', color: '#94a3b8' }}>
            {activeSignals.length} Active
          </span>
        </h3>
        <div style={{ fontSize: '12px', color: '#64748b' }}>
          AI Confidence &gt; 60%
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '20px' }}>
        {activeSignals.map(signal => {
          const statusColors = getStatusColor(signal.status)
          const rr = calculateRR(signal)
          const pnl = signal.direction === 'buy' 
            ? signal.currentPrice - signal.entryPrice 
            : signal.entryPrice - signal.currentPrice
          const pnlPercent = (pnl / signal.entryPrice) * 100
          const isProfit = pnl >= 0

          return (
            <div
              key={signal.id}
              style={{
                backgroundColor: '#0f172a',
                borderRadius: '12px',
                border: `1px solid ${statusColors.border}`,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}
            >
              {/* Header Section */}
              <div style={{ padding: '16px', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#fff' }}>{signal.pair}</span>
                    <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', backgroundColor: '#334155', color: '#cbd5e1' }}>
                      {signal.timeframe}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    {signal.strategy}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ 
                    fontSize: '11px', 
                    fontWeight: 'bold', 
                    color: statusColors.text,
                    backgroundColor: statusColors.bg,
                    padding: '4px 8px',
                    borderRadius: '6px',
                    display: 'inline-block',
                    marginBottom: '4px'
                  }}>
                    {signal.status.toUpperCase()}
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>{signal.timestamp}</div>
                </div>
              </div>

              {/* Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: '1px solid #1e293b' }}>
                <div style={{ padding: '12px', borderRight: '1px solid #1e293b', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>R:R Ratio</div>
                  <div style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>1:{rr}</div>
                </div>
                <div style={{ padding: '12px', borderRight: '1px solid #1e293b', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Win Prob</div>
                  <div style={{ fontSize: '14px', fontWeight: '600', color: signal.winProbability >= 70 ? '#10b981' : '#f59e0b' }}>
                    {signal.winProbability}%
                  </div>
                </div>
                <div style={{ padding: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Volatility</div>
                  <div style={{ fontSize: '14px', fontWeight: '600', color: signal.volatility === 'High' ? '#f59e0b' : signal.volatility === 'Extreme' ? '#ef4444' : '#34d399' }}>
                    {signal.volatility}
                  </div>
                </div>
              </div>

              {/* Main Content */}
              <div style={{ padding: '16px', flex: 1 }}>
                {/* Price Block */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '2px' }}>Entry</div>
                    <div style={{ fontSize: '15px', fontWeight: '600', color: '#fff' }}>{formatPrice(signal.entryPrice, signal.pair)}</div>
                  </div>
                  
                  {/* Direction Arrow */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    {signal.direction === 'buy' ? <TrendingUp size={24} color="#3b82f6" /> : <TrendingDown size={24} color="#ef4444" />}
                    <span style={{ fontSize: '10px', fontWeight: 'bold', color: signal.direction === 'buy' ? '#3b82f6' : '#ef4444', marginTop: '2px' }}>
                      {signal.direction.toUpperCase()}
                    </span>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '2px' }}>Current</div>
                    <div style={{ fontSize: '15px', fontWeight: '600', color: isProfit ? '#10b981' : '#ef4444' }}>
                      {formatPrice(signal.currentPrice, signal.pair)}
                    </div>
                    <div style={{ fontSize: '10px', color: isProfit ? '#10b981' : '#ef4444' }}>
                      {isProfit ? '+' : ''}{pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                </div>

                {/* Targets & Stop */}
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#ef4444' }}>
                      <Shield size={12} /> SL: {formatPrice(signal.stopLoss, signal.pair)}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#10b981' }}>
                      <Target size={12} /> Final TP: {formatPrice(signal.targets[signal.targets.length - 1], signal.pair)}
                    </div>
                  </div>
                  
                  {/* Multi-Target Progress */}
                  <div style={{ display: 'flex', gap: '4px', height: '6px', marginTop: '8px' }}>
                    {signal.targets.map((tp, idx) => {
                      const isHit = signal.direction === 'buy' ? signal.currentPrice >= tp : signal.currentPrice <= tp
                      return (
                        <div 
                          key={idx} 
                          style={{ 
                            flex: 1, 
                            backgroundColor: isHit ? '#10b981' : '#334155', 
                            borderRadius: '2px',
                            position: 'relative'
                          }}
                          title={`TP${idx+1}: ${tp}`}
                        />
                      )
                    })}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                    <span style={{ fontSize: '10px', color: '#64748b' }}>TP1</span>
                    <span style={{ fontSize: '10px', color: '#64748b' }}>TP2</span>
                    <span style={{ fontSize: '10px', color: '#64748b' }}>TP3</span>
                  </div>
                </div>

                {/* Confluence Tags */}
                <div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>Institutional Confluence:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {signal.confidence.map((factor, idx) => (
                      <span key={idx} style={{ 
                        fontSize: '10px', 
                        padding: '3px 8px', 
                        backgroundColor: '#1e293b', 
                        borderRadius: '12px', 
                        color: '#94a3b8',
                        border: '1px solid #334155'
                      }}>
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
