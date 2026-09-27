"""Import all models so Alembic autogenerate and db.create_all() see them."""
from app.models.bodyweight import BodyweightEntry  # noqa: F401
from app.models.exercise import Exercise, MuscleGroup  # noqa: F401
from app.models.exercise_template import ExerciseTemplate  # noqa: F401
from app.models.settings import UserSettings  # noqa: F401
from app.models.template import TemplateExercise, WorkoutTemplate  # noqa: F401
from app.models.workout import Workout, WorkoutExercise, WorkoutSet  # noqa: F401
