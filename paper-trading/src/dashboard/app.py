"""Flask application factory."""

from flask import Flask
from .routes import register_routes


def create_app(engine, dashboard_handler, config):
    """
    Create and configure the Flask application.

    engine: TradingEngine instance
    dashboard_handler: DashboardHandler for log access
    config: Config instance
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.config["engine"] = engine
    app.config["dashboard_handler"] = dashboard_handler
    app.config["app_config"] = config

    register_routes(app)

    return app
