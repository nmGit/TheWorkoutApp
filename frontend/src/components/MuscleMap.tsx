import { useEffect, useRef, useState } from 'react'
import { MuscleMapWidget, type BodySide, type Muscle } from '@abdofallah/musclemap-js'
import type { RegionFill } from '../lib/strengthColors'

export type { RegionFill }

const PRIMARY_COLOR = '#3b82f6'
const SECONDARY_COLOR = '#93c5fd'

interface Props {
  side: BodySide
  /** Regions the exercise works mainly, drawn strongest. */
  primary: Muscle[]
  /** Regions it works incidentally, drawn lighter. */
  secondary: Muscle[]
  /** Explicit colour per region. When given, it replaces primary and secondary. */
  fills?: RegionFill[]
  onRegionClick?: (region: Muscle) => void
  interactive?: boolean
  className?: string
}

/** A body diagram that highlights the regions worked. The canvas sizes itself to its
 * container, so the container must have a height. */
export function MuscleMap({
  side,
  primary,
  secondary,
  fills,
  onRegionClick,
  interactive = true,
  className = 'h-64 w-full',
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetRef = useRef<MuscleMapWidget | null>(null)
  // The widget is created once per side; keep the latest click handler without recreating it.
  const onClickRef = useRef(onRegionClick)
  onClickRef.current = onRegionClick

  // interactive is read once, when the widget is created.
  useEffect(() => {
    const widget = new MuscleMapWidget(containerRef.current!, {
      gender: 'male',
      side,
      interactive,
      showSubGroups: true,
      multiSelect: false,
      onMuscleClick: (region) => onClickRef.current?.(region),
    })
    widgetRef.current = widget
    // The library sets touch-action: none on its canvas, so a finger that starts on the map
    // can't scroll the page. Allow vertical panning; taps still reach the library.
    const canvas = containerRef.current!.querySelector('canvas')
    if (canvas) canvas.style.touchAction = 'pan-y'
    return () => {
      widget.destroy()
      widgetRef.current = null
    }
  }, [side])

  // Compared by their joined keys so an unchanged set of regions doesn't redraw.
  const primaryKey = primary.join(',')
  const secondaryKey = secondary.join(',')
  const fillsKey = fills ? JSON.stringify(fills) : ''
  useEffect(() => {
    const widget = widgetRef.current
    if (!widget) return
    if (fills) {
      // One bulk call: each highlight() would redraw the whole body.
      widget.setHighlightData(fills.map((f) => ({ muscle: f.region, color: f.color, opacity: f.opacity })))
      return
    }
    widget.clearHighlights()
    const secondaryOnly = secondary.filter((m) => !primary.includes(m))
    if (secondaryOnly.length) widget.highlightMany(secondaryOnly, SECONDARY_COLOR, 0.7)
    if (primary.length) widget.highlightMany(primary, PRIMARY_COLOR, 0.9)
  }, [primaryKey, secondaryKey, fillsKey, side])

  return <div ref={containerRef} className={className} />
}

/** Front and back diagrams for a set of muscles (canonical slugs). Each diagram draws
 * only once it's near the screen, so long lists of cards don't build hundreds of canvases. */
export function MuscleMapPair({
  primary,
  secondary,
  fills,
  onRegionClick,
  showLabels = false,
  interactive = true,
  className = 'h-64 w-full',
}: {
  /** Body regions worked mainly, and incidentally. */
  primary: Muscle[]
  secondary: Muscle[]
  fills?: RegionFill[]
  onRegionClick?: (region: Muscle) => void
  showLabels?: boolean
  interactive?: boolean
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (visible || !el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [visible])

  const primaryRegions = unique(primary)
  const secondaryRegions = unique(secondary).filter((r) => !primaryRegions.includes(r))
  const empty = !fills && primaryRegions.length === 0 && secondaryRegions.length === 0

  return (
    <div ref={ref} className={`grid grid-cols-2 grid-rows-1 gap-2 ${className}`}>
      {visible &&
        !empty &&
        (['front', 'back'] as const).map((side) => (
          <div key={side} className="flex h-full min-h-0 flex-col">
            {showLabels && <p className="mb-1 text-center text-xs capitalize text-muted">{side}</p>}
            <MuscleMap
              side={side}
              primary={primaryRegions}
              secondary={secondaryRegions}
              fills={fills}
              onRegionClick={onRegionClick}
              interactive={interactive}
              className="min-h-0 w-full flex-1"
            />
          </div>
        ))}
    </div>
  )
}

function unique<T>(items: T[]): T[] {
  return [...new Set(items)]
}
