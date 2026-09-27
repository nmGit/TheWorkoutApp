import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models.workout import Workout
from scripts.backfill_workout_names import backfill

CSV_HEADER = (
    "Workout #;Date;Workout Name;Duration (sec);Exercise Name;Set Order;"
    "Weight (kg);Reps;RPE;Distance (meters);Seconds;Notes;Workout Notes\n"
)


def _write_csv(tmp_path, rows: str):
    path = tmp_path / "export.csv"
    path.write_text(CSV_HEADER + rows, encoding="utf-8")
    return str(path)


def test_backfill_renames_and_retimes_matching_date(app, tmp_path):
    workout = Workout(
        name="Workout",
        started_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
        completed_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    db.session.add(workout)
    db.session.commit()
    workout_id = workout.id

    csv_path = _write_csv(
        tmp_path,
        '"1";"2024-03-01 18:30:00";"Leg Day";"3600";"Squat";"1";"100";"5";"";"";"";"";""\n',
    )

    backfill(csv_path)

    updated = db.session.get(Workout, workout_id)
    assert updated.name == "Leg Day"
    assert updated.started_at == datetime(2024, 3, 1, 18, 30, 0)
    assert updated.completed_at == datetime(2024, 3, 1, 19, 30, 0)


def test_backfill_is_idempotent(app, tmp_path, capsys):
    workout = Workout(
        name="Workout",
        started_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
        completed_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    db.session.add(workout)
    db.session.commit()

    csv_path = _write_csv(
        tmp_path,
        '"1";"2024-03-01 18:30:00";"Leg Day";"3600";"Squat";"1";"100";"5";"";"";"";"";""\n',
    )

    backfill(csv_path)
    capsys.readouterr()
    backfill(csv_path)
    out = capsys.readouterr().out
    assert "Renamed 0, re-timed 0, already correct 1." in out


def test_backfill_leaves_unmatched_dates_untouched(app, tmp_path):
    workout = Workout(
        name="Test",
        started_at=datetime(2026, 9, 27, 19, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 9, 27, 19, 6, tzinfo=timezone.utc),
    )
    db.session.add(workout)
    db.session.commit()
    workout_id = workout.id

    csv_path = _write_csv(
        tmp_path,
        '"1";"2024-03-01 18:30:00";"Leg Day";"3600";"Squat";"1";"100";"5";"";"";"";"";""\n',
    )

    backfill(csv_path)

    unchanged = db.session.get(Workout, workout_id)
    assert unchanged.name == "Test"


def test_backfill_ignores_workouts_with_no_completed_at(app, tmp_path):
    active = Workout(name="Workout", started_at=datetime(2024, 3, 1, tzinfo=timezone.utc))
    db.session.add(active)
    db.session.commit()
    active_id = active.id

    csv_path = _write_csv(
        tmp_path,
        '"1";"2024-03-01 18:30:00";"Leg Day";"3600";"Squat";"1";"100";"5";"";"";"";"";""\n',
    )

    backfill(csv_path)

    still_active = db.session.get(Workout, active_id)
    assert still_active.name == "Workout"
    assert still_active.completed_at is None
