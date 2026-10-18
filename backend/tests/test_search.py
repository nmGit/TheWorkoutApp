from app.services.search import fuzzy_rank, search_score


def test_exact_and_prefix_and_substring_all_match():
    assert search_score("bench press", "bench press") > 0
    assert search_score("bench", "bench press") > 0
    assert search_score("press", "bench press") > 0


def test_word_order_does_not_matter():
    # The previous plain substring match required this exact order and failed here.
    assert search_score("press bench", "Bench Press (Barbell)") > 0


def test_partial_word_still_matches():
    assert search_score("bar", "Barbell Row") > 0


def test_a_single_typo_still_matches():
    assert search_score("bemch press", "Bench Press") > 0
    assert search_score("suqat", "Barbell Squat") > 0


def test_unrelated_query_does_not_match():
    assert search_score("treadmill run", "Barbell Bench Press") == 0


def test_very_short_query_is_not_fuzzy_matched_into_everything():
    # "sq" is a substring of neither "Leg Press" nor "Row" -- too short to fuzzy-match either,
    # which a length-blind ratio comparison would otherwise do by sheer coincidence.
    assert search_score("sq", "Leg Press") == 0
    assert search_score("sq", "Row") == 0


def test_exact_match_ranks_above_a_looser_match():
    assert search_score("squat", "Squat") > search_score("squat", "Squat (Smith Machine)")


def test_a_clean_word_match_always_outranks_a_coincidental_fuzzy_one():
    # Real catalog bug caught live: "bench" happens to be a close edit-distance match for the
    # unrelated word "french" (sharing the substring "ench"), which must never outrank an
    # exercise that actually contains both query words cleanly.
    clean = search_score("press bench", "Bench Press (Barbell)")
    coincidental = search_score("press bench", "French Press On Exercise Ball")
    assert coincidental == 0.0
    assert clean > coincidental


def test_fuzzy_rank_drops_non_matches_and_orders_best_first():
    class Item:
        def __init__(self, name):
            self.name = name

    items = [Item("Barbell Squat"), Item("Squat"), Item("Treadmill Run"), Item("Front Squat")]
    ranked = fuzzy_rank(items, "squat")
    assert [i.name for i in ranked] == ["Squat", "Barbell Squat", "Front Squat"]


def test_fuzzy_rank_passes_through_unchanged_for_a_blank_query():
    class Item:
        def __init__(self, name):
            self.name = name

    items = [Item("B"), Item("A")]
    assert fuzzy_rank(items, "") == items
    assert fuzzy_rank(items, "   ") == items
