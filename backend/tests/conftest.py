import pytest

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # A separate in-memory database for the catalog bind, mirroring the two-file split in
    # production (a bare "sqlite:///:memory:" would otherwise just be the same kind of URI
    # reused, but SQLAlchemy gives each bind its own engine/connection, so this is already an
    # independent database -- not a size-of-one toy, the same separation prod has).
    SQLALCHEMY_BINDS = {"catalog": "sqlite:///:memory:"}
    TESTING = True


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def chest_group(app):
    group = MuscleGroup(name="Chest", display_order=0)
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture()
def bench_press(app, chest_group):
    exercise = ExerciseTemplate(
        name="Bench Press",
        muscle_group_id=chest_group.id,
        equipment="barbell",
        tracking_type="weight_reps",
    )
    db.session.add(exercise)
    db.session.commit()
    return exercise
