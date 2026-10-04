import type { Muscle } from '@abdofallah/musclemap-js'

/**
 * Which regions of the MuscleMapJS body each of our muscles lights up, keyed by the
 * canonical slug the backend sends (see canonical_muscle_slug in serializers.py).
 * A muscle with several regions lights them all. A muscle not listed here has no
 * region on the body and is shown as text only.
 *
 * Only base regions are listed. The widget hides sub-groups (front-deltoid,
 * upper-chest, ...) unless showSubGroups is set, so a sub-group region would never
 * draw. Those muscles go to their parent region instead.
 */
const REGIONS_FOR_SLUG: Record<string, Muscle[]> = {
  // Core
  rectus_abdominis: ['abs'],
  abdominals: ['abs'],
  transverse_abdominis: ['abs'],
  lower_abs: ['abs'],
  obliques: ['obliques'],
  // Chest
  pectoralis_major: ['chest'],
  chest: ['chest'],
  upper_chest: ['chest'],
  // Shoulders
  anterior_deltoid: ['deltoids'],
  lateral_deltoid: ['deltoids'],
  deltoids: ['deltoids'],
  delts: ['deltoids'],
  shoulders: ['deltoids'],
  posterior_deltoid: ['deltoids'],
  rear_deltoids: ['deltoids'],
  rotator_cuff: ['rotator-cuff'],
  supraspinatus: ['rotator-cuff'],
  // Back
  trapezius: ['trapezius'],
  levator_scapulae: ['trapezius'],
  upper_back: ['upper-back'],
  latissimus_dorsi: ['upper-back'],
  lats: ['upper-back'],
  rhomboids: ['rhomboids'],
  serratus_anterior: ['serratus'],
  erector_spinae: ['lower-back'],
  lower_back: ['lower-back'],
  quadratus_lumborum: ['lower-back'],
  // Arms
  biceps_brachii: ['biceps'],
  brachialis: ['biceps'],
  triceps_brachii: ['triceps'],
  brachioradialis: ['forearm'],
  forearm_flexors: ['forearm'],
  forearm_extensors: ['forearm'],
  forearms: ['forearm'],
  grip_muscles: ['forearm'],
  wrist_flexors: ['forearm'],
  wrist_extensors: ['forearm'],
  wrists: ['forearm'],
  hands: ['hands'],
  // Legs
  gluteus_maximus: ['gluteal'],
  gluteus_medius: ['gluteal'],
  hamstrings: ['hamstring'],
  quadriceps: ['quadriceps'],
  quads: ['quadriceps'],
  adductors: ['adductors'],
  groin: ['adductors'],
  inner_thighs: ['adductors'],
  hip_flexors: ['quadriceps'],
  calves: ['calves'],
  gastrocnemius: ['calves'],
  soleus: ['calves'],
  shins: ['tibialis'],
  feet: ['feet'],
  ankles: ['ankles'],
  ankle_stabilizers: ['ankles'],
  // Neck
  sternocleidomastoid: ['neck'],
}

export function regionsFor(slug: string): Muscle[] {
  return REGIONS_FOR_SLUG[slug] ?? []
}
