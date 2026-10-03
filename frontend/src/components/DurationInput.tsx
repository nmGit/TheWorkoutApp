import { useEffect, useState } from 'react'
import { formatRest, parseRest } from '../lib/format'

interface Props {
  /** The stored value in seconds, or null when none is set. */
  value: number | null
  /** Greyed-out ghost value shown while `value` is null. */
  placeholderSeconds?: number | null
  /** Called with the new seconds (or null if cleared) once editing finishes with a changed, valid value. */
  onCommit: (seconds: number | null) => void
  className?: string
  title?: string
  label?: string
}

/** A rest-duration field that shows and accepts M:SS ("1:30"), or plain
 * seconds ("90"). Commits when focus leaves the field (or on Enter); an
 * unparseable entry snaps back to the stored value. */
export function DurationInput({ value, placeholderSeconds, onCommit, className = '', title, label }: Props) {
  const shown = (v: number | null) => (v === null ? '' : formatRest(v))
  const [text, setText] = useState(shown(value))
  useEffect(() => setText(shown(value)), [value])

  const commit = () => {
    const parsed = parseRest(text)
    if (parsed === undefined) {
      setText(shown(value))
      return
    }
    setText(shown(parsed))
    if (parsed !== value) onCommit(parsed)
  }

  return (
    <input
      type="text"
      inputMode="text"
      value={text}
      placeholder={placeholderSeconds != null ? formatRest(placeholderSeconds) : 'm:ss'}
      title={title}
      aria-label={label}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') e.currentTarget.blur()
      }}
      className={className}
    />
  )
}
