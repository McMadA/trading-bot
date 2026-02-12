"""Flask routes — API endpoints and page routes."""

import logging
from flask import render_template, jsonify, request

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all routes on the Flask app."""

    def _get_engine():
        return app.config["engine"]

    def _get_handler():
        return app.config["dashboard_handler"]

    def _get_config():
        return app.config["app_config"]

    # ==================== PAGE ROUTES ====================

    @app.route("/")
    def index():
        config = _get_config()
        return render_template(
            "index.html",
            polling_interval=config.get("dashboard.polling_interval_ms", 5000),
        )

    @app.route("/backtest")
    def backtest_page():
        return render_template("backtest.html")

    # ==================== API ROUTES ====================

    @app.route("/api/portfolio")
    def api_portfolio():
        engine = _get_engine()
        summary = engine.portfolio.get_portfolio_summary(engine.current_prices)
        return jsonify(summary)

    @app.route("/api/positions")
    def api_positions():
        engine = _get_engine()
        positions = engine.portfolio.get_all_positions()
        prices = engine.current_prices
        return jsonify([_serialize_position(p, prices) for p in positions])

    @app.route("/api/orders")
    def api_orders():
        limit = request.args.get("limit", 50, type=int)
        engine = _get_engine()
        orders = engine.portfolio._db.get_orders(limit=limit)
        return jsonify([_serialize_order(o) for o in orders])

    @app.route("/api/trades")
    def api_trades():
        symbol = request.args.get("symbol")
        limit = request.args.get("limit", 100, type=int)
        engine = _get_engine()
        trades = engine.portfolio._db.get_trade_records(symbol=symbol, limit=limit)
        return jsonify([_serialize_trade(t) for t in trades])

    @app.route("/api/prices")
    def api_prices():
        engine = _get_engine()
        return jsonify(engine.current_prices)

    @app.route("/api/chart/<path:symbol>")
    def api_chart_data(symbol):
        engine = _get_engine()
        df = engine.get_pair_data(symbol)
        if df is None:
            return jsonify({"error": f"No data for {symbol}"}), 404

        return jsonify({
            "timestamps": df["timestamp"].dt.isoformat().tolist(),
            "open": df["open"].tolist(),
            "high": df["high"].tolist(),
            "low": df["low"].tolist(),
            "close": df["close"].tolist(),
            "volume": df["volume"].tolist(),
            "indicators": {
                col: df[col].tolist()
                for col in df.columns
                if col not in ["timestamp", "open", "high", "low", "close", "volume"]
            },
        })

    @app.route("/api/performance")
    def api_performance():
        engine = _get_engine()
        stats = engine.portfolio.get_performance_stats()
        snapshots = engine.portfolio._db.get_snapshots(hours=24 * 7)
        stats["equity_curve"] = [
            {"timestamp": s.timestamp.isoformat(), "value": s.total_value}
            for s in snapshots
        ]
        return jsonify(stats)

    @app.route("/api/logs")
    def api_logs():
        count = request.args.get("count", 50, type=int)
        handler = _get_handler()
        return jsonify({"logs": handler.get_records(count)})

    @app.route("/api/strategy", methods=["GET"])
    def api_get_strategy():
        engine = _get_engine()
        return jsonify({
            "name": engine.strategy.name,
            "config": engine.strategy._config,
        })

    @app.route("/api/strategy", methods=["POST"])
    def api_set_strategy():
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Missing 'name' field"}), 400
        engine = _get_engine()
        try:
            engine.change_strategy(data["name"], data.get("params"))
            return jsonify({"status": "ok", "strategy": data["name"]})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/engine/status")
    def api_engine_status():
        engine = _get_engine()
        return jsonify({
            "running": engine.is_running,
            "pairs": engine._pairs,
            "timeframe": engine._timeframe,
            "strategy": engine.strategy.name,
        })

    @app.route("/api/backtest", methods=["POST"])
    def api_run_backtest():
        from ..trading.backtester import Backtester
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        engine = _get_engine()
        config = _get_config()

        backtester = Backtester(config, engine._exchange)
        result = backtester.run(
            strategy_name=data.get("strategy", "ema_sma_crossover"),
            strategy_params=data.get("params", {}),
            symbols=data.get("symbols", ["BTC/USDT"]),
            timeframe=data.get("timeframe", "1h"),
            days=data.get("days", 30),
        )

        return jsonify({
            "total_return_pct": result.total_return_pct,
            "win_rate": result.win_rate,
            "max_drawdown_pct": result.max_drawdown_pct,
            "total_trades": result.total_trades,
            "avg_trade_pnl": result.avg_trade_pnl,
            "equity_curve": result.equity_curve,
            "trades": [_serialize_trade(t) for t in result.trades],
        })

    # ==================== SERIALIZATION HELPERS ====================

    def _serialize_position(pos, current_prices):
        return {
            "id": pos.id,
            "symbol": pos.symbol,
            "side": pos.side.value,
            "quantity": round(pos.quantity, 6),
            "entry_price": round(pos.entry_price, 4),
            "current_price": round(
                current_prices.get(pos.symbol, pos.current_price), 4
            ),
            "unrealized_pnl": round(pos.unrealized_pnl, 2),
            "stop_loss_price": round(pos.stop_loss_price, 4) if pos.stop_loss_price else None,
            "take_profit_price": round(pos.take_profit_price, 4) if pos.take_profit_price else None,
            "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
        }

    def _serialize_order(order):
        return {
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": round(order.quantity, 6),
            "price": round(order.price, 4) if order.price else None,
            "status": order.status.value,
            "filled_price": round(order.filled_price, 4) if order.filled_price else None,
            "fee": round(order.fee, 4),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "strategy_name": order.strategy_name,
        }

    def _serialize_trade(trade):
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side.value if hasattr(trade.side, "value") else trade.side,
            "entry_price": round(trade.entry_price, 4),
            "exit_price": round(trade.exit_price, 4),
            "quantity": round(trade.quantity, 6),
            "pnl": round(trade.pnl, 2),
            "pnl_pct": round(trade.pnl_pct, 2),
            "fees": round(trade.fees, 4),
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "strategy_name": trade.strategy_name,
            "duration_minutes": trade.duration_minutes,
        }
