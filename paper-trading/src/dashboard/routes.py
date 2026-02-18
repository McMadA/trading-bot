"""Flask routes — API endpoints and page routes."""

import logging
import threading
import uuid
import time
from flask import render_template, jsonify, request

logger = logging.getLogger(__name__)

# Global dictionary to store backtest/sweep tasks
# Structure: { task_id: { "status": "running"|"completed"|"error", "progress": int, "result": dict, "error_msg": str, "timestamp": float } }
BACKTEST_TASKS = {}
MAX_TASK_AGE_SECONDS = 3600  # Clean up tasks older than 1 hour


def register_routes(app):
    """Register all routes on the Flask app."""

    def _get_engine():
        return app.config["engine"]

    def _get_handler():
        return app.config["dashboard_handler"]

    def _get_config():
        return app.config["app_config"]

    def _cleanup_old_tasks():
        now = time.time()
        to_remove = [tid for tid, task in BACKTEST_TASKS.items() if now - task["timestamp"] > MAX_TASK_AGE_SECONDS]
        for tid in to_remove:
            if tid in BACKTEST_TASKS:
                del BACKTEST_TASKS[tid]

    def _run_backtest_task(task_id, config, exchange, kwargs):
        from ..trading.backtester import Backtester
        try:
            backtester = Backtester(config, exchange)

            def progress_cb(pct):
                if task_id in BACKTEST_TASKS:
                    BACKTEST_TASKS[task_id]["progress"] = round(pct, 1)

            # Inject callback
            kwargs["progress_callback"] = progress_cb

            result = backtester.run(**kwargs)

            if task_id in BACKTEST_TASKS:
                BACKTEST_TASKS[task_id]["status"] = "completed"
                BACKTEST_TASKS[task_id]["progress"] = 100
                BACKTEST_TASKS[task_id]["result"] = _serialize_backtest_result(result)
        except Exception as e:
            logger.error(f"Backtest task {task_id} failed: {e}")
            if task_id in BACKTEST_TASKS:
                BACKTEST_TASKS[task_id]["status"] = "error"
                BACKTEST_TASKS[task_id]["error_msg"] = str(e)

    def _run_sweep_task(task_id, config, exchange, kwargs):
        from ..trading.backtester import Backtester
        import itertools

        try:
            strategy_name = kwargs.get("strategy_name")
            symbols = kwargs.get("symbols")
            timeframe = kwargs.get("timeframe")
            days = kwargs.get("days")
            param_ranges = kwargs.get("param_ranges")
            base_params = kwargs.get("base_params")

            # Generate combinations
            param_names = list(param_ranges.keys())
            param_value_lists = []
            for name in param_names:
                r = param_ranges[name]
                min_val = r["min"]
                max_val = r["max"]
                step = r["step"]
                values = []
                v = min_val
                while v <= max_val + 1e-9:
                    values.append(round(v, 6))
                    v += step
                param_value_lists.append(values)

            combinations = list(itertools.product(*param_value_lists))
            total_combos = len(combinations)

            backtester = Backtester(config, exchange)
            historical_data = backtester.fetch_historical_data(symbols, timeframe, days)

            if not historical_data:
                raise ValueError("No historical data available")

            results = []
            for i, combo in enumerate(combinations):
                if task_id not in BACKTEST_TASKS:
                    break  # Task deleted?

                # Update progress
                progress = (i / total_combos) * 100
                BACKTEST_TASKS[task_id]["progress"] = round(progress, 1)

                params = {**base_params, **dict(zip(param_names, combo))}
                try:
                    # Run backtest (synchronously, no inner progress for sweep)
                    res = backtester.run(
                        strategy_name=strategy_name,
                        strategy_params=params,
                        symbols=symbols,
                        timeframe=timeframe,
                        days=days,
                        initial_balance=kwargs.get("initial_balance"),
                        stop_loss_pct=kwargs.get("stop_loss_pct"),
                        take_profit_pct=kwargs.get("take_profit_pct"),
                        historical_data=historical_data
                    )
                    results.append({
                        "params": params,
                        "total_return_pct": res.total_return_pct,
                        "win_rate": res.win_rate,
                        "max_drawdown_pct": res.max_drawdown_pct,
                        "total_trades": res.total_trades,
                        "avg_trade_pnl": res.avg_trade_pnl,
                        "strategy_name": strategy_name,
                    })
                except Exception as e:
                    logger.warning(f"Sweep combination {params} failed: {e}")

            # Sort results
            results.sort(key=lambda r: r["total_return_pct"], reverse=True)

            if task_id in BACKTEST_TASKS:
                BACKTEST_TASKS[task_id]["status"] = "completed"
                BACKTEST_TASKS[task_id]["progress"] = 100
                BACKTEST_TASKS[task_id]["result"] = {
                    "sweep_results": results,
                    "total_combinations": total_combos,
                    "strategy": strategy_name,
                    "symbols": symbols,
                    "timeframe": timeframe,
                    "days": days,
                }

        except Exception as e:
            logger.error(f"Sweep task {task_id} failed: {e}")
            if task_id in BACKTEST_TASKS:
                BACKTEST_TASKS[task_id]["status"] = "error"
                BACKTEST_TASKS[task_id]["error_msg"] = str(e)

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
            "timestamps": df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
            "open": df["open"].tolist(),
            "high": df["high"].tolist(),
            "low": df["low"].tolist(),
            "close": df["close"].tolist(),
            "volume": df["volume"].tolist(),
            "indicators": {
                col: df[col].fillna(0).tolist()
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
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        engine = _get_engine()
        config = _get_config()

        # Cleanup old tasks
        _cleanup_old_tasks()

        task_id = str(uuid.uuid4())
        BACKTEST_TASKS[task_id] = {
            "status": "running",
            "progress": 0,
            "result": None,
            "timestamp": time.time()
        }

        kwargs = {
            "strategy_name": data.get("strategy", "ema_sma_crossover"),
            "strategy_params": data.get("params", {}),
            "symbols": data.get("symbols", ["BTC/USDT"]),
            "timeframe": data.get("timeframe", "1h"),
            "days": data.get("days", 30),
            "initial_balance": data.get("initial_balance", 10000.0),
            "stop_loss_pct": data.get("stop_loss_pct"),
            "take_profit_pct": data.get("take_profit_pct"),
        }

        thread = threading.Thread(
            target=_run_backtest_task,
            args=(task_id, config, engine._exchange, kwargs),
            daemon=True
        )
        thread.start()

        return jsonify({"task_id": task_id, "status": "running"})

    @app.route("/api/backtest/sweep", methods=["POST"])
    def api_run_backtest_sweep():
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        engine = _get_engine()
        config = _get_config()

        # Cleanup old tasks
        _cleanup_old_tasks()

        task_id = str(uuid.uuid4())
        BACKTEST_TASKS[task_id] = {
            "status": "running",
            "progress": 0,
            "result": None,
            "timestamp": time.time()
        }

        kwargs = {
            "strategy_name": data.get("strategy", "ema_sma_crossover"),
            "symbols": data.get("symbols", ["BTC/USDT"]),
            "timeframe": data.get("timeframe", "1h"),
            "days": data.get("days", 30),
            "initial_balance": data.get("initial_balance", 10000.0),
            "stop_loss_pct": data.get("stop_loss_pct"),
            "take_profit_pct": data.get("take_profit_pct"),
            "param_ranges": data.get("param_ranges", {}),
            "base_params": data.get("base_params", {}),
        }

        thread = threading.Thread(
            target=_run_sweep_task,
            args=(task_id, config, engine._exchange, kwargs),
            daemon=True
        )
        thread.start()

        return jsonify({"task_id": task_id, "status": "running"})

    @app.route("/api/backtest/status/<task_id>")
    def api_backtest_status(task_id):
        if task_id not in BACKTEST_TASKS:
            return jsonify({"error": "Task not found"}), 404

        task = BACKTEST_TASKS[task_id]
        return jsonify({
            "status": task["status"],
            "progress": task["progress"],
            "result": task.get("result"),
            "error_msg": task.get("error_msg"),
        })

    # ==================== SERIALIZATION HELPERS ====================

    def _serialize_backtest_result(result):
        return {
            "total_return_pct": result.total_return_pct,
            "win_rate": result.win_rate,
            "max_drawdown_pct": result.max_drawdown_pct,
            "total_trades": result.total_trades,
            "avg_trade_pnl": result.avg_trade_pnl,
            "equity_curve": result.equity_curve,
            "trades": [_serialize_trade(t) for t in result.trades],
            "strategy_name": result.strategy_name,
            "strategy_params": result.strategy_params,
            "initial_balance": result.initial_balance,
            "stop_loss_pct": result.stop_loss_pct,
            "take_profit_pct": result.take_profit_pct,
        }

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
