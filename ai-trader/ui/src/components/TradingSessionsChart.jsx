import React, { useState, useEffect } from 'react'

export function TradingSessionsChart({ userTimezone = 'UTC' }) {
  const [currentHour, setCurrentHour] = useState(new Date().getUTCHours())

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentHour(new Date().getUTCHours())
    }, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  // Session timings in UTC
  const sessions = [
    {
      name: 'Asia/Tokyo',
      start: 0,
      end: 9,
      color: '#f59e0b', // Amber
      bgColor: 'rgba(245, 158, 11, 0.2)'
    },
    {
      name: 'London',
      start: 8,
      end: 16,
      color: '#3b82f6', // Blue
      bgColor: 'rgba(59, 130, 246, 0.2)'
    },
    {
      name: 'New York',
      start: 13,
      end: 22,
      color: '#10b981', // Green
      bgColor: 'rgba(16, 185, 129, 0.2)'
    }
  ]

  // Calculate overlaps
  const overlaps = [
    {
      name: 'London + New York',
      start: 13,
      end: 16,
      label: 'Peak Liquidity',
      color: 'rgba(139, 92, 246, 0.3)' // Purple
    },
    {
      name: 'Asia + London',
      start: 8,
      end: 9,
      label: 'Moderate Activity',
      color: 'rgba(236, 72, 153, 0.3)' // Pink
    }
  ]

  // Generate 24 hours
  const hours = Array.from({ length: 24 }, (_, i) => i)

  // Determine which sessions are currently active
  const getActiveSessions = () => {
    const active = []
    sessions.forEach(session => {
      if (currentHour >= session.start && currentHour < session.end) {
        active.push(session)
      }
    })
    return active
  }

  const activeSessions = getActiveSessions()

  return (
    <div style={{ padding: '24px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#fff', margin: 0 }}>
          🌍 Trading Sessions & Overlap (UTC)
        </h3>
        
        {/* Active Session Indicator */}
        <div style={{
          padding: '12px 20px',
          backgroundColor: activeSessions.length > 0 ? '#0f172a' : '#1e293b',
          borderRadius: '8px',
          border: activeSessions.length > 0 ? `2px solid ${activeSessions[0]?.color}` : '1px solid #334155',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          {activeSessions.length > 0 ? (
            <>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: activeSessions[0].color,
                animation: 'pulse 2s infinite',
                boxShadow: `0 0 10px ${activeSessions[0].color}`
              }} />
              <div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>ACTIVE NOW</div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: activeSessions[0].color }}>
                  {activeSessions.map(s => s.name).join(' + ')}
                </div>
              </div>
            </>
          ) : (
            <>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#64748b'
              }} />
              <div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>MARKET STATUS</div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#94a3b8' }}>
                  Between Sessions
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Add pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {sessions.map(session => (
          <div key={session.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '2px',
              backgroundColor: session.color
            }} />
            <span style={{ fontSize: '13px', color: '#94a3b8' }}>
              {session.name} ({session.start}:00-{session.end}:00)
            </span>
          </div>
        ))}
      </div>

      {/* Timeline Chart */}
      <div style={{ position: 'relative', marginTop: '30px' }}>
        {/* Hour markers */}
        <div style={{ display: 'flex', marginBottom: '8px' }}>
          {hours.map(hour => (
            <div
              key={hour}
              style={{
                flex: 1,
                textAlign: 'center',
                fontSize: '11px',
                color: hour === currentHour ? '#10b981' : '#64748b',
                fontWeight: hour === currentHour ? 'bold' : 'normal'
              }}
            >
              {hour === currentHour && '▼'}
              {hour === 0 || hour % 3 === 0 ? `${hour}h` : ''}
            </div>
          ))}
        </div>

        {/* Session rows */}
        <div style={{ position: 'relative' }}>
          {sessions.map((session, idx) => (
            <div key={session.name} style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                {session.name}
              </div>
              <div style={{ position: 'relative', height: '32px', backgroundColor: '#0f172a', borderRadius: '6px', overflow: 'hidden' }}>
                {/* Session bar */}
                <div style={{
                  position: 'absolute',
                  left: `${(session.start / 24) * 100}%`,
                  width: `${((session.end - session.start) / 24) * 100}%`,
                  height: '100%',
                  backgroundColor: session.bgColor,
                  border: `2px solid ${session.color}`,
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: session.color,
                  fontSize: '11px',
                  fontWeight: '600'
                }}>
                  {session.end - session.start} hrs
                </div>

                {/* Current time marker */}
                {currentHour >= session.start && currentHour < session.end && (
                  <div style={{
                    position: 'absolute',
                    left: `${(currentHour / 24) * 100}%`,
                    width: '2px',
                    height: '100%',
                    backgroundColor: '#10b981'
                  }} />
                )}
              </div>
            </div>
          ))}

          {/* Overlap visualization */}
          <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #334155' }}>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '12px', fontWeight: '600' }}>
              📊 Session Overlaps (High Liquidity)
            </div>
            <div style={{ position: 'relative', height: '40px', backgroundColor: '#0f172a', borderRadius: '6px', overflow: 'hidden' }}>
              {overlaps.map(overlap => (
                <div
                  key={overlap.name}
                  style={{
                    position: 'absolute',
                    left: `${(overlap.start / 24) * 100}%`,
                    width: `${((overlap.end - overlap.start) / 24) * 100}%`,
                    height: '100%',
                    backgroundColor: overlap.color,
                    border: '2px solid rgba(139, 92, 246, 0.6)',
                    borderRadius: '4px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '4px'
                  }}
                >
                  <div style={{ fontSize: '10px', color: '#fff', fontWeight: '600' }}>
                    {overlap.name}
                  </div>
                  <div style={{ fontSize: '9px', color: '#e2e8f0' }}>
                    {overlap.start}:00-{overlap.end}:00
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Info box */}
      <div style={{
        marginTop: '20px',
        padding: '12px',
        backgroundColor: '#0f172a',
        borderRadius: '8px',
        border: '1px solid #334155'
      }}>
        <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.6' }}>
          <strong style={{ color: '#fff' }}>💡 Trading Tips:</strong><br />
          • <strong style={{ color: '#8b5cf6' }}>London + NY Overlap (13:00-16:00 UTC)</strong> = Highest liquidity & volatility<br />
          • <strong style={{ color: '#ec4899' }}>Asia + London Overlap (08:00-09:00 UTC)</strong> = Moderate activity<br />
          • Current time: <strong style={{ color: '#10b981' }}>{currentHour}:00 UTC</strong>
        </div>
      </div>
    </div>
  )
}
