import React from 'react'

export function ActiveSignalsWidget() {
  // Mock active signals - one per major pair
  const activeSignals = [
    {
      pair: 'EURUSD',
      status: 'ongoing',
      direction: 'buy',
      entryPrice: 1.0465,
      currentPrice: 1.0482,
      stopLoss: 1.0435,
      target: 1.0525,
      winProbability: 68,
      timestamp: '2h ago'
    },
    {
      pair: 'GBPUSD',
      status: 'waiting',
      direction: 'sell',
      entryPrice: 1.2590,
      currentPrice: 1.2580,
      stopLoss: 1.2620,
      target: 1.2530,
      winProbability: 72,
      timestamp: '15m ago'
    },
    {
      pair: 'XAUUSD',
      status: 'succeeded',
      direction: 'buy',
      entryPrice: 4050.00,
      currentPrice: 4065.00,
      stopLoss: 4020.00,
      target: 4080.00,
      winProbability: 75,
      timestamp: '4h ago'
    },
    {
      pair: 'BTCUSD',
      status: 'ongoing',
      direction: 'buy',
      entryPrice: 84200.00,
      currentPrice: 84599.00,
      stopLoss: 83800.00,
      target: 85000.00,
      winProbability: 65,
      timestamp: '1h ago'
    }
  ]

  const getStatusColor = (status) => {
    switch(status) {
      case 'waiting': return { bg: '#1e40af', text: '#93c5fd', border: '#3b82f6' }
      case 'ongoing': return { bg: '#15803d', text: '#86efac', border: '#10b981' }
      case 'succeeded': return { bg: '#7c2d12', text: '#fdba74', border: '#f59e0b' }
      default: return { bg: '#374151', text: '#9ca3af', border: '#6b7280' }
    }
  }

  const getStatusIcon = (status) => {
    switch(status) {
      case 'waiting': return '⏳'
      case 'ongoing': return '📈'
      case 'succeeded': return '✅'
      default: return '•'
    }
  }

  const calculateProgress = (signal) => {
    const { entryPrice, currentPrice, target, stopLoss, direction } = signal
    
    if (direction === 'buy') {
      const totalDistance = target - entryPrice
      const currentDistance = currentPrice - entryPrice
      return Math.min(100, Math.max(0, (currentDistance / totalDistance) * 100))
    } else {
      const totalDistance = entryPrice - target
      const currentDistance = entryPrice - currentPrice
      return Math.min(100, Math.max(0, (currentDistance / totalDistance) * 100))
    }
  }

  return (
    <div style={{ padding: '24px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
      <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', color: '#fff' }}>
        🎯 Active Signals ({activeSignals.length})
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        {activeSignals.map(signal => {
          const statusColors = getStatusColor(signal.status)
          const progress = calculateProgress(signal)
          const pnl = signal.direction === 'buy' 
            ? signal.currentPrice - signal.entryPrice 
            : signal.entryPrice - signal.currentPrice
          const pnlPercent = (pnl / signal.entryPrice) * 100

          return (
            <div
              key={signal.pair}
              style={{
                padding: '16px',
                backgroundColor: '#0f172a',
                borderRadius: '8px',
                border: `2px solid ${statusColors.border}`,
                position: 'relative'
              }}
            >
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                <div>
                  <div style={{ fontSize: '16px', fontWeight: '600', color: '#fff' }}>{signal.pair}</div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>{signal.timestamp}</div>
                </div>
                <div style={{
                  padding: '4px 12px',
                  backgroundColor: statusColors.bg,
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: '600',
                  color: statusColors.text,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  {getStatusIcon(signal.status)} {signal.status.toUpperCase()}
                </div>
              </div>

              {/* Direction Badge */}
              <div style={{
                display: 'inline-block',
                padding: '4px 10px',
                backgroundColor: signal.direction === 'buy' ? '#1e40af' : '#991b1b',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: '600',
                color: '#fff',
                marginBottom: '12px'
              }}>
                {signal.direction.toUpperCase()}
              </div>

              {/* Price Levels */}
              <div style={{ marginBottom: '12px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ color: '#64748b' }}>Entry:</span>
                  <span style={{ color: '#fff', fontWeight: '600' }}>{signal.entryPrice.toFixed(signal.pair.includes('USD') && !signal.pair.includes('JPY') ? 4 : 2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ color: '#64748b' }}>Current:</span>
                  <span style={{ color: pnl >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                    {signal.currentPrice.toFixed(signal.pair.includes('USD') && !signal.pair.includes('JPY') ? 4 : 2)}
                    {' '}({pnl >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ color: '#64748b' }}>Stop Loss:</span>
                  <span style={{ color: '#ef4444', fontWeight: '600' }}>{signal.stopLoss.toFixed(signal.pair.includes('USD') && !signal.pair.includes('JPY') ? 4 : 2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Target:</span>
                  <span style={{ color: '#10b981', fontWeight: '600' }}>{signal.target.toFixed(signal.pair.includes('USD') && !signal.pair.includes('JPY') ? 4 : 2)}</span>
                </div>
              </div>

              {/* Progress Bar */}
              <div style={{ marginBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>
                  <span>Progress to Target</span>
                  <span>{progress.toFixed(0)}%</span>
                </div>
                <div style={{ 
                  width: '100%', 
                  height: '6px', 
                  backgroundColor: '#1e293b', 
                  borderRadius: '3px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${progress}%`,
                    height: '100%',
                    backgroundColor: progress >= 100 ? '#f59e0b' : '#10b981',
                    transition: 'width 0.3s ease',
                    borderRadius: '3px'
                  }} />
                </div>
              </div>

              {/* Win Probability */}
              <div style={{
                padding: '8px 12px',
                backgroundColor: '#1e293b',
                borderRadius: '6px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Win Probability</span>
                <span style={{ 
                  fontSize: '16px', 
                  fontWeight: 'bold',
                  color: signal.winProbability >= 70 ? '#10b981' : signal.winProbability >= 60 ? '#f59e0b' : '#ef4444'
                }}>
                  {signal.winProbability}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
