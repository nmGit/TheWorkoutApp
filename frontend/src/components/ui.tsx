import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-surface p-4 ${className}`}>{children}</div>
  )
}

export function PageTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h1 className="text-2xl font-bold">{children}</h1>
      {action}
    </div>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  const variants: Record<string, string> = {
    primary: 'bg-accent text-accent-fg hover:opacity-90',
    secondary: 'bg-border/60 text-fg hover:bg-border',
    ghost: 'text-fg hover:bg-border/40',
    danger: 'bg-danger text-white hover:opacity-90',
  }
  return (
    <button
      className={`rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    />
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-12 text-center">
      <p className="font-medium text-fg">{title}</p>
      {hint && <p className="max-w-xs text-sm text-muted">{hint}</p>}
      {action}
    </div>
  )
}

export function LoadingState() {
  return <p className="py-12 text-center text-sm text-muted">Loading…</p>
}

export function ErrorState({ message }: { message: string }) {
  return <p className="py-12 text-center text-sm text-danger">{message}</p>
}

export function ViewExerciseButton({ exerciseId }: { exerciseId: number }) {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => navigate(`/exercises/${exerciseId}`)}
      title="View exercise page (history & progress chart)"
      aria-label="View exercise page"
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted hover:bg-border/40 hover:text-fg"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 3v16a2 2 0 0 0 2 2h16" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M7 15l4-5 3 3 5-7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  )
}

export function Badge({ children, tone = 'default' }: { children: ReactNode; tone?: 'default' | 'warn' | 'accent' }) {
  const tones: Record<string, string> = {
    default: 'bg-border/60 text-muted',
    warn: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
    accent: 'bg-accent/15 text-accent',
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}>{children}</span>
  )
}
