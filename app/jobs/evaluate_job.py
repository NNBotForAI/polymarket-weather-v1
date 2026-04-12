"""Evaluate job — calculate P&L and accuracy stats."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func

from app.core.database import async_session
from app.models.evaluation_runs import EvaluationRun
from app.models.job_runs import JobRun
from app.models.paper_trades import PaperTrade

logger = logging.getLogger(__name__)


async def run_evaluate() -> dict:
    """Evaluate all closed paper trades and compute stats."""
    job = JobRun(
        job_name="evaluate",
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    async with async_session() as session:
        session.add(job)
        await session.flush()

        try:
            # Get all closed trades
            result = await session.execute(
                select(PaperTrade).where(PaperTrade.status == "closed")
            )
            closed_trades = result.scalars().all()

            if not closed_trades:
                eval_run = EvaluationRun(
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    total_pnl=0.0,
                    win_rate=0.0,
                    avg_edge=0.0,
                    evaluated_at=datetime.now(timezone.utc),
                )
                session.add(eval_run)
                job.status = "success"
                job.result_meta = {"total_trades": 0}
                await session.commit()
                return {"total_trades": 0}

            total = len(closed_trades)
            winning = sum(1 for t in closed_trades if t.pnl and float(t.pnl) > 0)
            losing = sum(1 for t in closed_trades if t.pnl and float(t.pnl) <= 0)
            total_pnl = sum(float(t.pnl or 0) for t in closed_trades)
            win_rate = winning / total if total > 0 else 0.0
            avg_pnl = total_pnl / total if total > 0 else 0.0

            # Build details
            by_direction = {"YES": {"count": 0, "pnl": 0.0}, "NO": {"count": 0, "pnl": 0.0}}
            for t in closed_trades:
                d = t.direction
                if d in by_direction:
                    by_direction[d]["count"] += 1
                    by_direction[d]["pnl"] += float(t.pnl or 0)

            details = {
                "total_pnl": round(total_pnl, 6),
                "avg_pnl_per_trade": round(avg_pnl, 6),
                "win_rate": round(win_rate, 4),
                "by_direction": by_direction,
            }

            eval_run = EvaluationRun(
                total_trades=total,
                winning_trades=winning,
                losing_trades=losing,
                total_pnl=round(total_pnl, 6),
                win_rate=round(win_rate, 4),
                avg_edge=round(avg_pnl, 6),
                details=details,
                evaluated_at=datetime.now(timezone.utc),
            )
            session.add(eval_run)

            job.status = "success"
            job.result_meta = {
                "total_trades": total,
                "winning": winning,
                "losing": losing,
                "total_pnl": round(total_pnl, 6),
                "win_rate": round(win_rate, 4),
            }

        except Exception as e:
            logger.exception("Evaluate job failed")
            job.status = "failed"
            job.error = str(e)

        job.finished_at = datetime.now(timezone.utc)
        await session.commit()

    logger.info("Evaluate complete: %s", job.result_meta)
    return job.result_meta or {}
