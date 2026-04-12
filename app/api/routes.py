"""API routes — markets, signals, trades, evaluations, jobs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.signal_scorer import score_signal
from app.engines.paper_trader import should_open_trade, create_trade_params
from app.models.evaluation_runs import EvaluationRun
from app.models.job_runs import JobRun
from app.models.markets import Market
from app.models.paper_trades import PaperTrade
from app.models.signal_scores import SignalScore

router = APIRouter()


# --- Markets ---

@router.get("/markets/recent")
async def get_recent_markets(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recently discovered weather markets."""
    result = await db.execute(
        select(Market)
        .where(Market.is_weather == True)
        .order_by(desc(Market.created_at))
        .limit(limit)
    )
    markets = result.scalars().all()
    return [
        {
            "id": m.id,
            "polymarket_id": m.polymarket_id,
            "question": m.question,
            "slug": m.slug,
            "is_weather": m.is_weather,
            "end_date": str(m.end_date) if m.end_date else None,
            "active": m.active,
            "closed": m.closed,
            "volume": float(m.volume) if m.volume else None,
            "liquidity": float(m.liquidity) if m.liquidity else None,
        }
        for m in markets
    ]


# --- Signals ---

@router.get("/signals/recent")
async def get_recent_signals(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent signal scores."""
    result = await db.execute(
        select(SignalScore)
        .order_by(desc(SignalScore.scored_at))
        .limit(limit)
    )
    signals = result.scalars().all()
    return [
        {
            "id": s.id,
            "market_id": s.market_id,
            "market_yes_price": float(s.market_yes_price) if s.market_yes_price else None,
            "weather_prob": float(s.weather_prob) if s.weather_prob else None,
            "edge": float(s.edge) if s.edge else None,
            "direction": s.direction,
            "confidence": s.confidence,
            "recommendation": s.recommendation,
            "scored_at": str(s.scored_at),
        }
        for s in signals
    ]


# --- Paper Trades ---

@router.get("/paper-trades/open")
async def get_open_trades(db: AsyncSession = Depends(get_db)):
    """Get all open paper trades."""
    result = await db.execute(
        select(PaperTrade, Market)
        .join(Market, PaperTrade.market_id == Market.id)
        .where(PaperTrade.status == "open")
        .order_by(desc(PaperTrade.opened_at))
    )
    trades = result.all()
    return [
        {
            "id": t.id,
            "market_id": t.market_id,
            "question": m.question,
            "direction": t.direction,
            "entry_price": float(t.entry_price),
            "quantity": float(t.quantity),
            "status": t.status,
            "opened_at": str(t.opened_at),
            "notes": t.notes,
        }
        for t, m in trades
    ]


@router.get("/paper-trades/resolved")
async def get_resolved_trades(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get resolved (closed) paper trades."""
    result = await db.execute(
        select(PaperTrade, Market)
        .join(Market, PaperTrade.market_id == Market.id)
        .where(PaperTrade.status == "closed")
        .order_by(desc(PaperTrade.closed_at))
        .limit(limit)
    )
    trades = result.all()
    return [
        {
            "id": t.id,
            "market_id": t.market_id,
            "question": m.question,
            "direction": t.direction,
            "entry_price": float(t.entry_price),
            "exit_price": float(t.exit_price) if t.exit_price else None,
            "pnl": float(t.pnl) if t.pnl else None,
            "status": t.status,
            "opened_at": str(t.opened_at),
            "closed_at": str(t.closed_at) if t.closed_at else None,
        }
        for t, m in trades
    ]


# --- Evaluations ---

@router.get("/evaluations/latest")
async def get_latest_evaluation(db: AsyncSession = Depends(get_db)):
    """Get the most recent evaluation run."""
    result = await db.execute(
        select(EvaluationRun)
        .order_by(desc(EvaluationRun.evaluated_at))
        .limit(1)
    )
    ev = result.scalar_one_or_none()
    if not ev:
        return {"message": "No evaluation runs yet"}
    return {
        "id": ev.id,
        "total_trades": ev.total_trades,
        "winning_trades": ev.winning_trades,
        "losing_trades": ev.losing_trades,
        "total_pnl": float(ev.total_pnl) if ev.total_pnl else None,
        "win_rate": float(ev.win_rate) if ev.win_rate else None,
        "details": ev.details,
        "evaluated_at": str(ev.evaluated_at),
    }


# --- Jobs ---

@router.post("/jobs/run-scan")
async def trigger_scan():
    """Trigger a market scan job."""
    from app.jobs import run_scan
    try:
        stats = await run_scan()
        return {"status": "completed", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/run-resolve")
async def trigger_resolve():
    """Trigger a resolve job."""
    from app.jobs.resolve_job import run_resolve
    try:
        stats = await run_resolve()
        return {"status": "completed", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/run-evaluate")
async def trigger_evaluate():
    """Trigger an evaluation job."""
    from app.jobs.evaluate_job import run_evaluate
    try:
        stats = await run_evaluate()
        return {"status": "completed", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
