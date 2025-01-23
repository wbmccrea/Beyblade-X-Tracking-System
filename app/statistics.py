from sqlalchemy import func, case, and_, or_, desc, Float
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import math
from .models import Match, Player, BeybladeCombination, TournamentParticipant

K_FACTOR = 32  # K-factor for ELO calculation

def calculate_expected_score(rating1: int, rating2: int) -> float:
    """Calculates the expected score for player 1 against player 2."""
    return 1 / (1 + 10 ** ((rating2 - rating1) / 400))

def update_elo_ratings(db: Session, match: Match):
    """Updates ELO ratings for players and combinations after a match."""
    combination1_participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.combination_id == match.combination1_id, TournamentParticipant.tournament_id == match.tournament_id)
        .first()
    )
    combination2_participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.combination_id == match.combination2_id, TournamentParticipant.tournament_id == match.tournament_id)
        .first()
    )

    if not combination1_participant or not combination2_participant:
        return  # Participants not found, can't update ELO

    rating1 = combination1_participant.elo_rating
    rating2 = combination2_participant.elo_rating

    expected_score1 = calculate_expected_score(rating1, rating2)
    expected_score2 = calculate_expected_score(rating2, rating1)

    actual_score1 = 1 if (match.combination1_id == match.winner_id) else 0
    actual_score2 = 1 if (match.combination2_id == match.winner_id) else 0

    new_rating1 = rating1 + K_FACTOR * (actual_score1 - expected_score1)
    new_rating2 = rating2 + K_FACTOR * (actual_score2 - expected_score2)

    combination1_participant.elo_rating = round(new_rating1)
    combination2_participant.elo_rating = round(new_rating2)

    # Update player ELO ratings as well
    player1_participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.player_id == match.player1_id, TournamentParticipant.tournament_id == match.tournament_id)
        .first()
    )
    player2_participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.player_id == match.player2_id, TournamentParticipant.tournament_id == match.tournament_id)
        .first()
    )

    if player1_participant and player2_participant:
        player1_rating = player1_participant.elo_rating
        player2_rating = player2_participant.elo_rating

        player1_expected_score = calculate_expected_score(player1_rating, rating2)
        player2_expected_score = calculate_expected_score(player2_rating, rating1)

        player1_actual_score = actual_score1
        player2_actual_score = actual_score2

        player1_new_rating = player1_rating + K_FACTOR * (player1_actual_score - player1_expected_score)
        player2_new_rating = player2_rating + K_FACTOR * (player2_actual_score - player2_expected_score)

        player1_participant.elo_rating = round(player1_new_rating)
        player2_participant.elo_rating = round(player2_new_rating)

    db.commit()

def calculate_player_matches_played(db: Session, player_id: int):
    """Calculates the total matches played by a player."""
    return db.query(Match).filter(or_(Match.player1_id == player_id, Match.player2_id == player_id)).count()

def calculate_player_wins(db: Session, player_id: int):
    """Calculates the total wins for a player."""
    return db.query(Match).filter(Match.winner_id == player_id).count()

def calculate_player_losses(db: Session, player_id: int):
    """Calculates the total losses for a player."""
    return db.query(Match).filter(
        or_(
            and_(Match.player1_id == player_id, Match.winner_id != player_id, Match.draw == False),
            and_(Match.player2_id == player_id, Match.winner_id != player_id, Match.draw == False)
        )
    ).count()

def calculate_player_draws(db: Session, player_id: int):
    """Calculates the total draws for a player."""
    return db.query(Match).filter(
        or_(
            and_(Match.player1_id == player_id, Match.draw == True),
            and_(Match.player2_id == player_id, Match.draw == True)
        )
    ).count()

def calculate_player_win_percentage(db: Session, player_id: int):
    """Calculates the win percentage for a player."""
    matches_played = calculate_player_matches_played(db, player_id)
    draws = calculate_player_draws(db, player_id)
    wins = calculate_player_wins(db, player_id)

    if (matches_played - draws) == 0:
        return 0.0
    return (wins / (matches_played - draws)) * 100

def calculate_player_non_loss_percentage(db: Session, player_id: int):
    """Calculates the non-loss percentage (wins + draws) for a player."""
    matches_played = calculate_player_matches_played(db, player_id)
    wins = calculate_player_wins(db, player_id)
    draws = calculate_player_draws(db, player_id)
    if matches_played == 0:
      return 0.0
    return ((wins + draws) / matches_played) * 100

def calculate_player_total_points(db: Session, player_id: int):
    """Calculates the total points for a given player."""
    total_points = db.query(func.sum(case(
        (Match.winner_id == player_id, case(
            (Match.finish_type == "Burst", 2),
            (Match.finish_type == "KO", 2),
            (Match.finish_type == "Extreme", 3),
            else_=1
        )),
        else_=0
    ))).filter(or_(Match.player1_id == player_id, Match.player2_id == player_id)).scalar()
    return total_points if total_points is not None else 0

def calculate_player_average_points_per_match(db: Session, player_id: int):
    """Calculates the average points per match for a player."""
    total_points = calculate_player_total_points(db, player_id)
    matches_played = calculate_player_matches_played(db, player_id)
    if matches_played == 0:
        return 0
    return total_points / matches_played

def calculate_player_most_common_winning_finish_type(db: Session, player_id: int):
    """Calculates the most common winning finish type for a player."""
    most_common_finish = (
        db.query(Match.finish_type)
        .filter(Match.winner_id == player_id)
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_finish[0] if most_common_finish else None

def calculate_player_win_streak(db: Session, player_id: int):
    """Calculates the current win streak for a player."""

    winning_matches = (
        db.query(Match)
        .filter(Match.winner_id == player_id)
        .order_by(Match.end_time.desc())  # Order by match time descending
        .all()
    )

    if not winning_matches:
        return 0

    streak = 0
    for match in winning_matches:
        if match.winner_id == player_id:
            streak += 1
        else:
            break  # Streak broken

    return streak

def calculate_player_loss_streak(db: Session, player_id: int):
    """Calculates the current loss streak for a player."""
    losing_matches = (
        db.query(Match)
        .filter(or_(
            and_(Match.player1_id == player_id, Match.winner_id != player_id, Match.draw == False),
            and_(Match.player2_id == player_id, Match.winner_id != player_id, Match.draw == False)
        ))
        .order_by(Match.end_time.desc())
        .all()
    )
    if not losing_matches:
        return 0

    streak = 0
    for match in losing_matches:
        if (match.player1_id == player_id and match.winner_id != player_id) or (match.player2_id == player_id and match.winner_id != player_id):
            streak += 1
        else:
            break
    return streak

def calculate_player_elo_rating(db: Session, player_id: int, tournament_id: int):
    """Gets the ELO rating of a player in a given tournament."""
    participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.player_id == player_id, TournamentParticipant.tournament_id == tournament_id)
        .first()
    )
    return participant.elo_rating if participant else None

def calculate_combination_matches_played(db: Session, combination_id: int):
    """Calculates the total matches played by a combination."""
    return db.query(Match).filter(
        or_(
            Match.combination1_id == combination_id,
            Match.combination2_id == combination_id
        )
    ).count()

def calculate_combination_wins(db: Session, combination_id: int):
    """Calculates the total wins for a combination."""
    return db.query(Match).filter(
        or_(
            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id),
            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id)
        )
    ).count()

def calculate_combination_losses(db: Session, combination_id: int):
    """Calculates the total losses for a combination."""
    return db.query(Match).filter(
        or_(
            and_(Match.combination1_id == combination_id, Match.player1_id != Match.winner_id, Match.draw == False),
            and_(Match.combination2_id == combination_id, Match.player2_id != Match.winner_id, Match.draw == False)
        )
    ).count()

def calculate_combination_draws(db: Session, combination_id: int):
    """Calculates the total draws for a combination."""
    return db.query(Match).filter(
        or_(
            and_(Match.combination1_id == combination_id, Match.draw == True),
            and_(Match.combination2_id == combination_id, Match.draw == True)
        )
    ).count()

def calculate_combination_win_percentage(db: Session, combination_id: int):
    """Calculates the win percentage for a combination."""
    matches_played = calculate_combination_matches_played(db, combination_id)
    draws = calculate_combination_draws(db, combination_id)
    wins = calculate_combination_wins(db, combination_id)
    if (matches_played - draws) == 0:
        return 0.0
    return (wins / (matches_played - draws)) * 100

def calculate_combination_non_loss_percentage(db: Session, combination_id: int):
    """Calculates the non-loss percentage (wins + draws) for a combination."""
    matches_played = calculate_combination_matches_played(db, combination_id)
    wins = calculate_combination_wins(db, combination_id)
    draws = calculate_combination_draws(db, combination_id)
    if matches_played == 0:
        return 0.0
    return ((wins + draws) / matches_played) * 100

def calculate_combination_total_points(db: Session, combination_id: int):
    """Calculates the total points for a given combination."""
    total_points = db.query(func.sum(case(
        (and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id), case(
            (Match.finish_type == "Burst", 2),
            (Match.finish_type == "KO", 2),
            (Match.finish_type == "Extreme", 3),
            else_=1
        )),
        (and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id), case(
            (Match.finish_type == "Burst", 2),
            (Match.finish_type == "KO", 2),
            (Match.finish_type == "Extreme", 3),
            else_=1
        )),
        else_=0
    ))).filter(or_(Match.combination1_id == combination_id, Match.combination2_id == combination_id)).scalar()
    return total_points if total_points is not None else 0

def calculate_combination_average_points_per_match(db: Session, combination_id: int):
    """Calculates the average points per match for a combination."""
    total_points = calculate_combination_total_points(db, combination_id)
    matches_played = calculate_combination_matches_played(db, combination_id)
    if matches_played == 0:
        return 0
    return total_points / matches_played

def calculate_combination_most_common_winning_finish_type(db: Session, combination_id: int):
    """Calculates the most common winning finish type for a combination."""
    most_common_finish = (
        db.query(Match.finish_type)
        .filter(or_(
            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id),
            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id)
        ))
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_finish[0] if most_common_finish else None

def calculate_combination_burst_rate(db: Session, combination_id: int):
    """Calculates the burst rate for a combination."""
    burst_wins = db.query(Match).filter(
        or_(
            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id, Match.finish_type == "Burst"),
            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id, Match.finish_type == "Burst")
        )
    ).count()
    wins = calculate_combination_wins(db, combination_id)
    if wins == 0:
        return 0.0
    return (burst_wins / wins) * 100

def calculate_combination_most_common_loss_type(db: Session, combination_id: int):
    """Calculates the most common loss type for a combination."""
    most_common_loss = (
        db.query(Match.finish_type)
        .filter(or_(
            and_(Match.combination1_id == combination_id, Match.player1_id != Match.winner_id, Match.draw == False),
            and_(Match.combination2_id == combination_id, Match.player2_id != Match.winner_id, Match.draw == False)
        ))
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_loss[0] if most_common_loss else None

def calculate_combination_most_common_opponent(db: Session, combination_id: int):
    """Calculates the most common opponent combination for a given combination."""

    opponent_counts = (
        db.query(
            case(
                (Match.combination1_id != combination_id, Match.combination1_id),
                (Match.combination2_id != combination_id, Match.combination2_id),
            ).label("opponent_id"),
            func.count().label("count")
        )
        .filter(
            or_(
                Match.combination1_id == combination_id,
                Match.combination2_id == combination_id
            ),
            Match.combination1_id != Match.combination2_id # filter out matches against itself
        )
        .group_by("opponent_id")
        .order_by(desc("count"))
        .all()
    )
    if opponent_counts:
        most_common_opponent_id = opponent_counts[0].opponent_id
        return most_common_opponent_id
    else:
        return None
    
def calculate_combination_best_matchups(db: Session, combination_id: int):
    """Calculates the best matchups (highest win rate) for a combination."""
    subquery = (
        db.query(
            case(
                (Match.combination1_id != combination_id, Match.combination1_id),
                (Match.combination2_id != combination_id, Match.combination2_id),
            ).label("opponent_id"),
            func.count().label("matches_played"),
            func.sum(
                case(
                    (
                        or_(
                            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id),
                            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id)
                        ),
                        1
                    ),
                    else_=0
                )
            ).label("wins")
        )
        .filter(
            or_(
                Match.combination1_id == combination_id,
                Match.combination2_id == combination_id
            ),
            Match.combination1_id != Match.combination2_id
        )
        .group_by("opponent_id")
        .subquery()
    )

    best_matchups = (
        db.query(subquery.c.opponent_id, (subquery.c.wins.cast(Float) / subquery.c.matches_played).label("win_rate"))
        .order_by(desc("win_rate"))
        .limit(5)  # Limit to top 5
        .all()
    )
    return best_matchups

def calculate_combination_worst_matchups(db: Session, combination_id: int):
    """Calculates the worst matchups (lowest win rate) for a combination."""
    subquery = (
        db.query(
            case(
                (Match.combination1_id != combination_id, Match.combination1_id),
                (Match.combination2_id != combination_id, Match.combination2_id),
            ).label("opponent_id"),
            func.count().label("matches_played"),
            func.sum(
                case(
                    (
                        or_(
                            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id),
                            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id)
                        ),
                        1
                    ),
                    else_=0
                )
            ).label("wins")
        )
        .filter(
            or_(
                Match.combination1_id == combination_id,
                Match.combination2_id == combination_id
            ),
            Match.combination1_id != Match.combination2_id
        )
        .group_by("opponent_id")
        .subquery()
    )

    worst_matchups = (
        db.query(subquery.c.opponent_id, (subquery.c.wins.cast(Float) / subquery.c.matches_played).label("win_rate"))
        .order_by("win_rate")
        .limit(5)  # Limit to top 5
        .all()
    )
    return worst_matchups

def calculate_combination_elo_rating(db: Session, combination_id: int, tournament_id: int):
    """Gets the ELO rating of a combination in a given tournament."""
    participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.combination_id == combination_id, TournamentParticipant.tournament_id == tournament_id)
        .first()
    )
    return participant.elo_rating if participant else None
