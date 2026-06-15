"""Flask application factory"""

import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from app.extensions import db, jwt, socketio


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)

    if config_object is None:
        from config import DevelopmentConfig
        config_object = DevelopmentConfig

    app.config.from_object(config_object)

    # 文件日志（按大小滚动，最多 5 个文件，每个 10MB）
    if not app.debug:
        handler = RotatingFileHandler("logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","msg":"%(message)s"}'
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

    db.init_app(app)
    jwt.init_app(app)

    # Register JWT token blocklist check (revoked tokens are rejected)
    from app.extensions import is_token_revoked
    jwt.token_in_blocklist_loader(is_token_revoked)

    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))
    socketio.init_app(app, cors_allowed_origins="*")

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_health_check(app)

    # Start WebSocket push services (pass app for context)
    from app.websocket.dashboard_pusher import start_dashboard_push
    from app.websocket.event_log_pusher import start_event_push, send_cached_events
    start_dashboard_push(app, interval=5.0)
    start_event_push(app, interval=2.0)

    # Send cached events only to the newly connected client
    @socketio.on("connect")
    def on_connect():
        from flask import request
        send_cached_events(sid=request.sid)

    return app


def _register_blueprints(app: Flask):
    from app.auth.routes import auth_bp
    from app.api.recommendations import recommendations_bp
    from app.api.metrics import metrics_bp
    from app.api.content import content_bp
    from app.api.users import users_bp
    from app.api.coldstart import coldstart_bp
    from app.api.export_routes import export_bp
    from app.api.admin import admin_bp
    from app.api.region import region_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(recommendations_bp, url_prefix="/api")
    app.register_blueprint(metrics_bp, url_prefix="/api")
    app.register_blueprint(content_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(coldstart_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(region_bp, url_prefix="/api")


def _register_error_handlers(app: Flask):
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)


def _register_health_check(app: Flask):
    @app.route("/api/health")
    def health_check():
        return {"status": "healthy", "service": "hybrid-recommender-api"}
