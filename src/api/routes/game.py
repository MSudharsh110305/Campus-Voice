from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from src.api.dependencies import get_db, get_current_student
from src.database.models import GameScore

router = APIRouter(prefix="/game", tags=["Game"])


class ScoreSubmit(BaseModel):
    score: int
    coins_earned: int = 0


class SpendCoins(BaseModel):
    amount: int


class LeaderboardEntry(BaseModel):
    rank: int
    score: int


class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardEntry]
    my_best: Optional[int] = None
    my_rank: Optional[int] = None
    my_coins: Optional[int] = None


@router.post("/score", status_code=status.HTTP_200_OK)
async def submit_score(
    body: ScoreSubmit,
    db: AsyncSession = Depends(get_db),
    roll_no: str = Depends(get_current_student),
):
    """Save student's best score (update only if higher) and add coins earned."""
    result = await db.execute(
        select(GameScore).where(GameScore.student_roll_no == roll_no)
    )
    existing = result.scalar_one_or_none()
    if existing:
        if body.score > existing.score:
            existing.score = body.score
        existing.coins = (existing.coins or 0) + body.coins_earned
    else:
        db.add(GameScore(student_roll_no=roll_no, score=body.score, coins=body.coins_earned))
    await db.commit()
    return {"success": True}


@router.post("/spend-coins", status_code=status.HTTP_200_OK)
async def spend_coins(
    body: SpendCoins,
    db: AsyncSession = Depends(get_db),
    roll_no: str = Depends(get_current_student),
):
    """Deduct coins from student's balance (for shop purchases)."""
    result = await db.execute(
        select(GameScore).where(GameScore.student_roll_no == roll_no)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="No game record found")
    current_coins = existing.coins or 0
    if current_coins < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient coins")
    existing.coins = current_coins - body.amount
    await db.commit()
    return {"success": True, "new_balance": existing.coins}


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
    roll_no: str = Depends(get_current_student),
):
    """Top 10 scores (one per student). Also returns caller's personal best, rank, and coin balance."""
    result = await db.execute(
        select(GameScore).order_by(GameScore.score.desc()).limit(10)
    )
    top = result.scalars().all()

    leaderboard = [{"rank": i + 1, "score": s.score} for i, s in enumerate(top)]

    my_best = None
    my_rank = None
    my_coins = None

    for i, s in enumerate(top):
        if s.student_roll_no == roll_no:
            my_best = s.score
            my_rank = i + 1
            my_coins = s.coins or 0
            break

    # If not in top-10, fetch separately
    if my_best is None:
        my_result = await db.execute(
            select(GameScore).where(GameScore.student_roll_no == roll_no)
        )
        my_entry = my_result.scalar_one_or_none()
        if my_entry:
            my_best = my_entry.score
            my_coins = my_entry.coins or 0
            rank_count = await db.execute(
                select(func.count()).select_from(GameScore).where(GameScore.score > my_entry.score)
            )
            my_rank = rank_count.scalar() + 1
        else:
            my_coins = 0

    return {"leaderboard": leaderboard, "my_best": my_best, "my_rank": my_rank, "my_coins": my_coins}
