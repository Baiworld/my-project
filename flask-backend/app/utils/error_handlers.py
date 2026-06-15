"""Unified error response formatting"""

import traceback
import uuid
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError


def register_error_handlers(app):
    """Register all error handlers on the Flask app"""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"code": 400, "error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"code": 401, "error": "Unauthorized", "message": "Invalid or expired token"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"code": 403, "error": "Forbidden", "message": "Insufficient permissions"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"code": 404, "error": "Not found", "message": str(e)}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"code": 500, "error": "Internal server error", "message": "An unexpected error occurred"}), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(e):
        """Database errors: rollback session, log details, return structured error."""
        from app.extensions import db
        db.session.rollback()
        error_id = uuid.uuid4().hex[:8]
        app.logger.error(f"[DB-{error_id}] {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return jsonify({
            "code": 500,
            "error": "Database error",
            "error_id": error_id,
            "message": "A database error occurred. The operation has been rolled back.",
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        """Catch-all for unexpected exceptions. Rollback DB, log, return structured error."""
        from app.extensions import db
        try:
            db.session.rollback()
        except Exception:
            pass
        error_id = uuid.uuid4().hex[:8]
        app.logger.error(f"[ERR-{error_id}] {type(e).__name__}: {e} | {request.method} {request.path}\n{traceback.format_exc()}")
        return jsonify({
            "code": 500,
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again later.",
        }), 500
