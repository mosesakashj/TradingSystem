import React from 'react'

export function PriceCard({ pair }) {
  // Format price with proper decimals
  const formatPrice = (price) => {
    if (!price) return '-'
    const decimals = pair.symbol?.includes('JPY') ? 2 : (pair.symbol?.includes('BTC') || pair.symbol?.includes('ETH')) ? 2 : 4
    return typeof price === 'number' ? price.toFixed(decimals) : price
  }

  return (
    <div style={{
      padding: '16px',
      backgroundColor: '#0f172a',
      borderRadius: '8px',
      border: `1px solid ${pair.marketOpen ? '#334155' : '#7f1d1d'}`,
      position: 'relative'
    }}>
      {!pair.marketOpen && (
        <div style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          padding: '4px 8px',
          backgroundColor: '#7f1d1d',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: '600',
          color: '#fca5a5'
        }}>
          CLOSED
        </div>
      )}
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: '600', color: '#fff' }}>{pair.symbol}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{pair.name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#fff' }}>{formatPrice(pair.price)}</div>
          <div style={{
            fontSize: '12px',
            color: (pair.change || 0) >= 0 ? '#10b981' : '#ef4444',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            marginTop: '2px'
          }}>
            {(pair.change || 0) >= 0 ? '▲' : '▼'} {Math.abs(pair.change || 0).toFixed(2)}%
          </div>
        </div>
      </div>

      {pair.marketOpen && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '6px' }}>
            <span>Buy {pair.buyPercent}%</span>
            <span>Sell {pair.sellPercent}%</span>
          </div>
          <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{
              width: `${pair.buyPercent}%`,
              backgroundColor: '#10b981',
              transition: 'width 0.3s ease'
            }} />
            <div style={{
              width: `${pair.sellPercent}%`,
              backgroundColor: '#ef4444',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <div style={{
            marginTop: '8px',
            fontSize: '11px',
            color: '#64748b',
            textAlign: 'center'
          }}>
            Sentiment: <span style={{
              color: pair.buyPercent > 60 ? '#10b981' : pair.sellPercent > 60 ? '#ef4444' : '#f59e0b',
              fontWeight: '600'
            }}>
              {pair.buyPercent > 60 ? 'Bullish' : pair.sellPercent > 60 ? 'Bearish' : 'Neutral'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
