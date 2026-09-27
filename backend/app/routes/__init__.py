from flask import Flask

from app.validation import ApiError, error_response


def register_routes(app: Flask) -> None:
    from app.routes.exercises import bp as exercises_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.stats import bp as stats_bp
    from app.routes.templates import bp as templates_bp
    from app.routes.workouts import bp as workouts_bp

    app.register_blueprint(exercises_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(workouts_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(settings_bp)

    @app.errorhandler(ApiError)
    def _handle_api_error(err: ApiError):
        return error_response(err.message, err.status)
