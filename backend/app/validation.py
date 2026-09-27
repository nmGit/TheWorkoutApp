from flask import jsonify


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def error_response(message: str, status: int = 400):
    return jsonify({"error": message}), status


def require(body: dict, *fields: str):
    missing = [f for f in fields if body.get(f) in (None, "")]
    if missing:
        raise ApiError(f"Missing required field(s): {', '.join(missing)}")
