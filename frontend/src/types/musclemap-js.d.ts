// The slice of @abdofallah/musclemap-js this app uses. The package ships TypeScript
// source that our strict compiler settings reject (unused locals inside node_modules),
// so the real source is never type-checked here. Vite still bundles the real code.
declare module '@abdofallah/musclemap-js' {
  /** The 36 body regions the library can highlight. */
  export type Muscle =
    | 'abs' | 'biceps' | 'calves' | 'chest' | 'deltoids'
    | 'feet' | 'forearm' | 'gluteal' | 'hamstring' | 'hands'
    | 'head' | 'knees' | 'lower-back' | 'obliques' | 'quadriceps'
    | 'tibialis' | 'trapezius' | 'triceps' | 'upper-back'
    | 'rotator-cuff' | 'serratus' | 'rhomboids'
    | 'ankles' | 'adductors' | 'neck' | 'hip-flexors'
    | 'upper-chest' | 'lower-chest' | 'inner-quad' | 'outer-quad'
    | 'upper-abs' | 'lower-abs' | 'front-deltoid' | 'rear-deltoid'
    | 'upper-trapezius' | 'lower-trapezius'

  export type BodySide = 'front' | 'back'
  export type MuscleSide = 'left' | 'right' | 'both'

  export interface MuscleMapOptions {
    gender?: 'male' | 'female'
    side?: BodySide
    interactive?: boolean
    /** Draw the sub-regions (front and rear deltoid, upper chest, ...) as their own parts. */
    showSubGroups?: boolean
    multiSelect?: boolean
    onMuscleClick?: (muscle: Muscle, side: MuscleSide) => void
  }

  export class MuscleMapWidget {
    constructor(container: HTMLElement, options?: MuscleMapOptions)
    highlight(muscle: Muscle, color: string, opacity?: number): void
    setHighlightData(data: Array<{ muscle: Muscle; color: string; opacity?: number }>): void
    highlightMany(muscles: Muscle[], color: string, opacity?: number): void
    clearHighlights(): void
    destroy(): void
  }
}
