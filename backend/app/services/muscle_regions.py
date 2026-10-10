"""Which body-diagram regions each muscle lights up.

Every colour on the body diagram comes through this mapping, both the strength colours and
the recency colours, and the app's own decisions (such as what to plan next) read the same
muscle data. Keys are canonical muscle slugs (see canonical_muscle_slug). A muscle with no
entry has no region on the diagram.

Several muscles can share a region, and a region takes the most recent or the average of its
muscles, depending on what is being shown.
"""

# Canonical muscle -> the diagram regions it lights up. Each muscle has its own region wherever the
# body diagram has one, including its sub-regions (front and rear deltoid, upper chest, hip flexors,
# upper trapezius). The few muscles the diagram can't separate share a region.
SLUG_REGIONS: dict[str, list[str]] = {
    "pectoralis_major": ["chest"],
    "upper_chest": ["upper-chest"],
    "serratus_anterior": ["serratus"],
    "latissimus_dorsi": ["upper-back"],
    "upper_back": ["upper-back"],
    "rhomboids": ["rhomboids"],
    "trapezius": ["trapezius"],
    "levator_scapulae": ["upper-trapezius"],
    "erector_spinae": ["lower-back"],
    "quadratus_lumborum": ["lower-back"],
    "rotator_cuff": ["rotator-cuff"],
    "anterior_deltoid": ["front-deltoid"],
    "lateral_deltoid": ["deltoids"],
    "posterior_deltoid": ["rear-deltoid"],
    "biceps_brachii": ["biceps"],
    "brachialis": ["biceps"],
    "brachioradialis": ["forearm"],
    "triceps_brachii": ["triceps"],
    "forearm_flexors": ["forearm"],
    "forearm_extensors": ["forearm"],
    "wrist_flexors": ["forearm"],
    "wrist_extensors": ["forearm"],
    "rectus_abdominis": ["abs"],
    "transverse_abdominis": ["abs"],
    "obliques": ["obliques"],
    "gluteus_maximus": ["gluteal"],
    "gluteus_medius": ["gluteal"],
    "adductors": ["adductors"],
    "hamstrings": ["hamstring"],
    "quadriceps": ["quadriceps"],
    "hip_flexors": ["hip-flexors"],
    "gastrocnemius": ["calves"],
    "soleus": ["calves"],
    "tibialis": ["tibialis"],
    "sternocleidomastoid": ["neck"],
}


def regions_for(slug: str) -> list[str]:
    return list(SLUG_REGIONS.get(slug, []))
