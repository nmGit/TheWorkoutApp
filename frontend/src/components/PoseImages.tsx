/** An exercise's images. With two poses (start/peak) they alternate as a
 * 2-frame animation (one second each); under prefers-reduced-motion both are
 * shown side by side instead -- see .pose-* in index.css. */
export function PoseImages({ urls, alt }: { urls: string[]; alt: string }) {
  if (urls.length === 0) return null
  if (urls.length === 1) {
    return <img src={urls[0]} alt={alt} className="mx-auto h-40 w-40 rounded-lg bg-border/40 object-cover" />
  }
  return (
    <>
      <div
        className="pose-animated relative mx-auto h-40 w-40 overflow-hidden rounded-lg bg-border/40"
        role="img"
        aria-label={`${alt}: start and end positions`}
      >
        <img src={urls[0]} alt="" className="pose-frame absolute inset-0 h-full w-full object-cover" />
        <img src={urls[1]} alt="" className="pose-frame pose-frame-b absolute inset-0 h-full w-full object-cover" />
      </div>
      <div className="pose-static justify-center gap-2">
        <img src={urls[0]} alt={`${alt}: start`} className="h-32 w-32 rounded-lg bg-border/40 object-cover" />
        <img src={urls[1]} alt={`${alt}: end`} className="h-32 w-32 rounded-lg bg-border/40 object-cover" />
      </div>
    </>
  )
}
