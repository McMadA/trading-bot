"""Entry point for the paper trading application."""

import os
import sys
import logging

# Ensure src is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.config import Config
from src.utils.logger import setup_logging
from src.data.database import Database
from src.trading.engine import TradingEngine
from src.dashboard.app import create_app


def main():
    # 1. Load configuration
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = Config.get_instance(config_path)

    # 2. Setup logging
    dashboard_handler = setup_logging(config)
    logger = logging.getLogger(__name__)
    logger.info("Paper Trading System starting...")

    # 3. Initialize database
    db_path = config.get("database.path", "data/paper_trading.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = Database(db_path)
    logger.info(f"Database initialized at {db_path}")

    # 4. Create and start trading engine
    engine = TradingEngine(config, db)
    engine.start()

    # 5. Create Flask app
    app = create_app(engine, dashboard_handler, config)

    # 6. Run Flask (blocking — engine runs in APScheduler background thread)
    host = config.get("dashboard.host", "0.0.0.0")
    port = config.get("dashboard.port", 5000)
    logger.info(f"Dashboard available at http://{host}:{port}")

    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
