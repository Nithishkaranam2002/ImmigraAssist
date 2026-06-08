interface BarItem {
  label: string
  value: number
  color?: string
}

interface TrendPoint {
  label: string
  value: number
}

interface StackedBar {
  label: string
  positive: number
  negative: number
}

const DEFAULT_COLORS = ["#4f46e5", "#818cf8", "#10b981", "#f59e0b", "#f43f5e", "#94a3b8"]

export function HorizontalBars({ items }: { items: BarItem[] }) {
  const max = Math.max(...items.map((i) => i.value), 1)
  return (
    <div className="space-y-3 h-full flex flex-col justify-center">
      {items.map((item) => (
        <div key={item.label}>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-600 capitalize">{item.label}</span>
            <span className="font-medium text-slate-800">{item.value}</span>
          </div>
          <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(item.value / max) * 100}%`,
                backgroundColor: item.color || "#4f46e5",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export function VerticalBars({ items }: { items: BarItem[] }) {
  const max = Math.max(...items.map((i) => i.value), 1)
  return (
    <div className="h-full flex items-end justify-around gap-2 pt-4">
      {items.map((item, i) => (
        <div key={item.label} className="flex flex-col items-center flex-1 min-w-0">
          <span className="text-[10px] font-medium text-slate-700 mb-1">{item.value}</span>
          <div
            className="w-full max-w-[40px] rounded-t-md transition-all duration-500"
            style={{
              height: `${Math.max((item.value / max) * 140, 4)}px`,
              backgroundColor: item.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length],
            }}
          />
          <span className="text-[9px] text-slate-500 mt-1.5 truncate w-full text-center capitalize">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  )
}

export function AreaTrend({ points, color = "#4f46e5" }: { points: TrendPoint[]; color?: string }) {
  if (!points.length) return null
  const max = Math.max(...points.map((p) => p.value), 1)
  const w = 100
  const h = 40
  const coords = points.map((p, i) => {
    const x = points.length === 1 ? w / 2 : (i / (points.length - 1)) * w
    const y = h - (p.value / max) * h
    return `${x},${y}`
  })
  const line = coords.join(" ")
  const area = `0,${h} ${line} ${w},${h}`

  return (
    <div className="h-full flex flex-col">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full flex-1 min-h-[120px]" preserveAspectRatio="none">
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={area} fill="url(#areaFill)" />
        <polyline points={line} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="flex justify-between text-[9px] text-slate-400 mt-1 px-0.5">
        <span>{points[0]?.label}</span>
        <span>{points[points.length - 1]?.label}</span>
      </div>
    </div>
  )
}

export function LineTrend({ points, color = "#10b981" }: { points: TrendPoint[]; color?: string }) {
  if (!points.length) return null
  const max = Math.max(...points.map((p) => p.value), 1)
  const w = 100
  const h = 40
  const coords = points.map((p, i) => {
    const x = points.length === 1 ? w / 2 : (i / (points.length - 1)) * w
    const y = h - (p.value / max) * h
    return `${x},${y}`
  })

  return (
    <div className="h-full flex flex-col">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full flex-1 min-h-[120px]" preserveAspectRatio="none">
        <polyline
          points={coords.join(" ")}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
        {points.map((p, i) => {
          const x = points.length === 1 ? w / 2 : (i / (points.length - 1)) * w
          const y = h - (p.value / max) * h
          return <circle key={i} cx={x} cy={y} r="1.2" fill={color} />
        })}
      </svg>
      <div className="flex justify-between text-[9px] text-slate-400 mt-1">
        <span>{points[0]?.label}</span>
        <span>{points[points.length - 1]?.label}</span>
      </div>
    </div>
  )
}

export function DonutChart({ items }: { items: BarItem[] }) {
  const total = items.reduce((s, i) => s + i.value, 0) || 1
  let offset = 0
  const segments = items.map((item, i) => {
    const pct = item.value / total
    const seg = { ...item, pct, offset, color: item.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length] }
    offset += pct
    return seg
  })

  return (
    <div className="h-full flex items-center gap-4">
      <div className="relative w-28 h-28 shrink-0">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#f1f5f9" strokeWidth="3.5" />
          {segments.map((seg) => (
            <circle
              key={seg.label}
              cx="18"
              cy="18"
              r="15.9"
              fill="none"
              stroke={seg.color}
              strokeWidth="3.5"
              strokeDasharray={`${seg.pct * 100} ${100 - seg.pct * 100}`}
              strokeDashoffset={`${-seg.offset * 100}`}
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold text-slate-800">{total}</span>
        </div>
      </div>
      <div className="space-y-1.5 min-w-0 flex-1">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: seg.color }} />
            <span className="text-slate-600 truncate">{seg.label}</span>
            <span className="font-medium text-slate-800 ml-auto">{seg.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function StackedBars({ items }: { items: StackedBar[] }) {
  const max = Math.max(...items.map((i) => i.positive + i.negative), 1)
  return (
    <div className="h-full flex items-end justify-around gap-2 pt-4">
      {items.map((item) => {
        const total = item.positive + item.negative
        return (
          <div key={item.label} className="flex flex-col items-center flex-1 min-w-0">
            <div
              className="w-full max-w-[36px] flex flex-col-reverse rounded-t-md overflow-hidden"
              style={{ height: `${Math.max((total / max) * 140, 4)}px` }}
            >
              <div
                className="w-full bg-emerald-500"
                style={{ height: total ? `${(item.positive / total) * 100}%` : "0%" }}
              />
              <div
                className="w-full bg-rose-500"
                style={{ height: total ? `${(item.negative / total) * 100}%` : "0%" }}
              />
            </div>
            <span className="text-[9px] text-slate-500 mt-1.5">{item.label}</span>
          </div>
        )
      })}
    </div>
  )
}
