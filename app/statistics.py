from sqlalchemy import func, case, and_, or_, desc, Float, cast
from sqlalchemy.orm import Session
from .models import Match, Player, BeybladeCombination, TournamentParticipant, Blade, Ratchet, Bit, Stadium, StadiumClass, Launcher, LauncherClass
import math
from datetime import datetime, timedelta

K_FACTOR = 32  # K-factor for ELO calculation (adjust as needed)

def calculate_expected_score(rating1: int, rating2: int) -> float:
    """Calculates the expected score for player 1 against player 2."""
    return 1 / (1 + 10 ** ((rating2 - rating1) / 400))

def update_elo_ratings(db: Session, match: Match):
    """Updates ELO ratings for players and combinations after a match."""
    # ... (ELO update logic - same as before, but now based on the correct models)

# --- Player Statistics Functions ---

def calculate_player_matches_played(db: Session, player_id: int):
    """Calculates the total matches played by a player."""
    return db.query(func.count()).filter(or_(Match.player1_id == player_id, Match.player2_id == player_id)).scalar()

def calculate_player_wins(db: Session, player_id: int):
    """Calculates the total wins for a player."""
    return db.query(func.count()).filter(Match.winner_id == player_id).scalar()

def calculate_player_losses(db: Session, player_id: int):
    """Calculates the total losses for a player."""
    return db.query(func.count()).filter(or_(and_(Match.player1_id == player_id, Match.winner_id != player_id, Match.draw == False), and_(Match.player2_id == player_id, Match.winner_id != player_id, Match.draw == False))).scalar()

def calculate_player_draws(db: Session, player_id: int):
    """Calculates the total draws for a player."""
    return db.query(func.count()).filter(or_(and_(Match.player1_id == player_id, Match.draw == True), and_(Match.player2_id == player_id, Match.draw == True))).scalar()

# ... (Previous Player Statistics functions)

def calculate_player_win_percentage(db: Session, player_id: int):
    """Calculates the win percentage for a player."""
    matches_played = calculate_player_matches_played(db, player_id)
    if matches_played == 0:
        return 0.0
    wins = calculate_player_wins(db, player_id)
    return (wins / matches_played) * 100

def calculate_player_non_loss_percentage(db: Session, player_id: int):
    """Calculates the non-loss percentage (wins + draws) for a player."""
    matches_played = calculate_player_matches_played(db, player_id)
    if matches_played == 0:
        return 0.0
    wins = calculate_player_wins(db, player_id)
    draws = calculate_player_draws(db, player_id)
    return ((wins + draws) / matches_played) * 100

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
        .order_by(Match.end_time.desc())
        .all()
    )
    if not winning_matches:
        return 0
    streak = 0
    for match in winning_matches:
        if match.winner_id == player_id:
            streak += 1
        else:
            break
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

# ... (Previous Player Statistics functions)

def calculate_player_total_points(db: Session, player_id: int, tournament_id: int):
    """Calculates the total points for a given player in a given tournament."""
    total_points = db.query(func.sum(case(
        (Match.winner_id == player_id, case(
            (Match.finish_type == "Burst", 2),
            (Match.finish_type == "KO", 2),
            (Match.finish_type == "Extreme", 3),
            else_=1
        )),
        else_=0
    ))).filter(or_(Match.player1_id == player_id, Match.player2_id == player_id), Match.tournament_id == tournament_id).scalar()
    return total_points if total_points is not None else 0

def calculate_player_average_points_per_match(db: Session, player_id: int, tournament_id: int):
    """Calculates the average points per match for a player in a given tournament."""
    total_points = calculate_player_total_points(db, player_id, tournament_id)
    matches_played = db.query(func.count()).filter(or_(Match.player1_id == player_id, Match.player2_id == player_id), Match.tournament_id == tournament_id).scalar()
    if matches_played == 0:
        return 0
    return total_points / matches_played

def calculate_player_elo_rating(db: Session, player_id: int, tournament_id: int):
    """Gets the ELO rating of a player in a given tournament."""
    participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.player_id == player_id, TournamentParticipant.tournament_id == tournament_id)
        .first()
    )
    return participant.elo_rating if participant else None

# --- Combination Statistics Functions ---

def calculate_combination_matches_played(db: Session, combination_id: int):
    """Calculates the total matches played by a combination."""
    return db.query(func.count()).filter(or_(Match.combination1_id == combination_id, Match.combination2_id == combination_id)).scalar()

def calculate_combination_wins(db: Session, combination_id: int):
    """Calculates the total wins for a combination."""
    return db.query(func.count()).filter(or_(and_(Match.combination1_id == combination_id, Match.winner_id == Match.player1_id), and_(Match.combination2_id == combination_id, Match.winner_id == Match.player2_id))).scalar()

def calculate_combination_losses(db: Session, combination_id: int):
    """Calculates the total losses for a combination."""
    return db.query(func.count()).filter(or_(and_(Match.combination1_id == combination_id, Match.winner_id != Match.player1_id, Match.draw == False), and_(Match.combination2_id == combination_id, Match.winner_id != Match.player2_id, Match.draw == False))).scalar()

def calculate_combination_draws(db: Session, combination_id: int):
    """Calculates the total draws for a combination."""
    return db.query(func.count()).filter(or_(and_(Match.combination1_id == combination_id, Match.draw == True), and_(Match.combination2_id == combination_id, Match.draw == True))).scalar()

# ... (Previous Combination Statistics functions)

def calculate_combination_win_percentage(db: Session, combination_id: int):
    """Calculates the win percentage for a combination."""
    matches_played = calculate_combination_matches_played(db, combination_id)
    if matches_played == 0:
        return 0.0
    wins = calculate_combination_wins(db, combination_id)
    return (wins / matches_played) * 100

def calculate_combination_non_loss_percentage(db: Session, combination_id: int):
    """Calculates the non-loss percentage (wins + draws) for a combination."""
    matches_played = calculate_combination_matches_played(db, combination_id)
    if matches_played == 0:
        return 0.0
    wins = calculate_combination_wins(db, combination_id)
    draws = calculate_combination_draws(db, combination_id)
    return ((wins + draws) / matches_played) * 100

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
    """Calculates the burst rate for a combination (burst wins / total wins)."""
    wins = calculate_combination_wins(db, combination_id)
    if wins == 0:
        return 0.0
    burst_wins = (
        db.query(func.count())
        .filter(or_(
            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id, Match.finish_type == "Burst"),
            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id, Match.finish_type == "Burst")
        ))
        .scalar()
    )
    return (burst_wins / wins) * 100

def calculate_combination_most_common_loss_type(db: Session, combination_id: int):
    """Calculates the most common loss type for a combination."""
    most_common_loss = (
        db.query(Match.finish_type)
        .filter(or_(
            and_(Match.combination1_id == combination_id, Match.winner_id != Match.player1_id, Match.draw == False),
            and_(Match.combination2_id == combination_id, Match.winner_id != Match.player2_id, Match.draw == False)
        ))
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_loss[0] if most_common_loss else None

# ... (Previous Combination Statistics functions)

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
            Match.combination1_id != Match.combination2_id
        )
        .group_by("opponent_id")
        .order_by(desc("count"))
        .first()
    )
    if opponent_counts:
        return opponent_counts[0].opponent_id
    else:
        return None

def calculate_combination_best_matchups(db: Session, combination_id: int):
    """Calculates the best matchups (highest win rate) for a combination."""
    # ... (Implementation using subquery, similar to previous version, but using correct model)

def calculate_combination_worst_matchups(db: Session, combination_id: int):
    """Calculates the worst matchups (lowest win rate) for a combination."""
    # ... (Implementation using subquery, similar to previous version, but using correct model)

def calculate_combination_total_points(db: Session, combination_id: int, tournament_id: int):
    """Calculates the total points for a given combination in a given tournament."""
    total_points = db.query(func.sum(case(
        (and_(Match.combination1_id == combination_id, Match.winner_id == Match.player1_id), case(
            (Match.finish_type == "Burst", 2),
            (Match.finish_type == "KO", 2),
            (Match.finish_type == "Extreme", 3),
            else_=1
        )),
        (and_(Match.combination2_id == combination_id, Match.winner_id == Match.player2_id), case(
            (Match.finish_type == "Burst", 2),
            (Match.finish_type == "KO", 2),
            (Match.finish_type == "Extreme", 3),
            else_=1
        )),
        else_=0
    ))).filter(or_(Match.combination1_id == combination_id, Match.combination2_id == combination_id), Match.tournament_id == tournament_id).scalar()
    return total_points if total_points is not None else 0

def calculate_combination_average_points_per_match(db: Session, combination_id: int, tournament_id: int):
    """Calculates the average points per match for a combination in a given tournament."""
    total_points = calculate_combination_total_points(db, combination_id, tournament_id)
    matches_played = db.query(func.count()).filter(or_(Match.combination1_id == combination_id, Match.combination2_id == combination_id), Match.tournament_id == tournament_id).scalar()
    if matches_played == 0:
        return 0
    return total_points / matches_played

def calculate_combination_elo_rating(db: Session, combination_id: int, tournament_id: int):
    """Gets the ELO rating of a combination in a given tournament."""
    participant = (
        db.query(TournamentParticipant)
        .filter(TournamentParticipant.combination_id == combination_id, TournamentParticipant.tournament_id == tournament_id)
        .first()
    )
    return participant.elo_rating if participant else None

# ... (Previous Combination Statistics functions)

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
        db.query(subquery.c.opponent_id, (cast(subquery.c.wins, Float) / subquery.c.matches_played).label("win_rate"))
        .order_by(desc("win_rate"))
        .limit(5)
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
        db.query(subquery.c.opponent_id, (cast(subquery.c.wins, Float) / subquery.c.matches_played).label("win_rate"))
        .order_by("win_rate")
        .limit(5)
        .all()
    )
    return worst_matchups

# --- Beyblade Part Statistics Functions (Blade, Ratchet, Bit) ---

def calculate_part_usage_frequency(db: Session, part_type: str, part_id: int):
    """Calculates the usage frequency of a Beyblade part."""
    if part_type == "Blade":
        return db.query(func.count()).filter(BeybladeCombination.blade_id == part_id).scalar()
    elif part_type == "Ratchet":
        return db.query(func.count()).filter(BeybladeCombination.ratchet_id == part_id).scalar()
    elif part_type == "Bit":
        return db.query(func.count()).filter(BeybladeCombination.bit_id == part_id).scalar()
    else:
        return 0
    
# ... (Previous Beyblade Part Statistics functions)

def calculate_part_win_rate(db: Session, part_type: str, part_id: int):
    """Calculates the win rate of combinations using a specific Beyblade part."""
    if part_type == "Blade":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.blade_id == part_id).all()
    elif part_type == "Ratchet":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.ratchet_id == part_id).all()
    elif part_type == "Bit":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.bit_id == part_id).all()
    else:
        return 0.0

    if not combinations:
        return 0.0

    total_wins = 0
    total_matches = 0
    for combination_id_tuple in combinations:
        combination_id = combination_id_tuple[0]
        total_wins += calculate_combination_wins(db, combination_id)
        total_matches += calculate_combination_matches_played(db, combination_id)
    
    if total_matches == 0:
        return 0.0

    return (total_wins / total_matches) * 100

def calculate_most_common_combinations_with_part(db: Session, part_type: str, part_id: int):
    """Calculates the most common combinations that include a specific part."""
    if part_type == "Blade":
        return db.query(BeybladeCombination).filter(BeybladeCombination.blade_id == part_id).all()
    elif part_type == "Ratchet":
        return db.query(BeybladeCombination).filter(BeybladeCombination.ratchet_id == part_id).all()
    elif part_type == "Bit":
        return db.query(BeybladeCombination).filter(BeybladeCombination.bit_id == part_id).all()
    else:
        return []

def calculate_part_total_points(db: Session, part_type: str, part_id: int, tournament_id: int):
    """Calculates the total points accumulated by combinations using this part in a given tournament."""
    if part_type == "Blade":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.blade_id == part_id).all()
    elif part_type == "Ratchet":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.ratchet_id == part_id).all()
    elif part_type == "Bit":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.bit_id == part_id).all()
    else:
        return 0

    total_points = 0
    for combination_id_tuple in combinations:
        combination_id = combination_id_tuple[0]
        total_points += calculate_combination_total_points(db, combination_id, tournament_id)
    return total_points

def calculate_part_average_points_per_match(db: Session, part_type: str, part_id: int, tournament_id: int):
    """Calculates the average points per match accumulated by combinations using this part in a given tournament."""
    total_points = calculate_part_total_points(db, part_type, part_id, tournament_id)
    if part_type == "Blade":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.blade_id == part_id).all()
    elif part_type == "Ratchet":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.ratchet_id == part_id).all()
    elif part_type == "Bit":
        combinations = db.query(BeybladeCombination.combination_id).filter(BeybladeCombination.bit_id == part_id).all()
    else:
        return 0
    total_matches = 0
    for combination_id_tuple in combinations:
        combination_id = combination_id_tuple[0]
        total_matches += calculate_combination_matches_played(db, combination_id)
    if total_matches == 0:
        return 0
    return total_points / total_matches

# ... (Previous functions)

# --- Stadium Statistics Functions ---

def calculate_matches_played_in_stadium(db: Session, stadium_id: int):
    """Calculates the total matches played in a specific stadium."""
    return db.query(func.count()).filter(Match.stadium_id == stadium_id).scalar()

def calculate_win_percentage_by_stadium(db: Session, stadium_id: int, participant_type, participant_id):
    """Calculates the win percentage for a given participant in a specific stadium."""
    if participant_type not in ("Player", "Combination"):
        return 0.0

    if participant_type == "Player":
        wins = db.query(func.count()).filter(Match.stadium_id == stadium_id, Match.winner_id == participant_id).scalar()
        matches = db.query(func.count()).filter(Match.stadium_id == stadium_id, or_(Match.player1_id == participant_id, Match.player2_id == participant_id)).scalar()
    elif participant_type == "Combination":
        wins = db.query(func.count()).filter(Match.stadium_id == stadium_id, or_(
                and_(Match.combination1_id == participant_id, Match.player1_id == Match.winner_id),
                and_(Match.combination2_id == participant_id, Match.player2_id == Match.winner_id)
            )).scalar()
        matches = db.query(func.count()).filter(Match.stadium_id == stadium_id, or_(Match.combination1_id == participant_id, Match.combination2_id == participant_id)).scalar()
    else:
        return 0.0

    if matches == 0:
        return 0.0
    return (wins / matches) * 100

def calculate_most_common_win_type_by_stadium(db: Session, stadium_id: int):
    """Calculates the most common win type in a specific stadium."""
    most_common_win_type = (
        db.query(Match.finish_type)
        .filter(Match.stadium_id == stadium_id)
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_win_type[0] if most_common_win_type else None

def calculate_most_common_matchups_in_stadium(db: Session, stadium_id: int, participant_type):
    """Calculates the most common matchups in a specific stadium."""
    if participant_type not in ("Player", "Combination"):
        return []

    match_id_column1 = Match.player1_id if participant_type == "Player" else Match.combination1_id
    match_id_column2 = Match.player2_id if participant_type == "Player" else Match.combination2_id

    matchups = (
        db.query(match_id_column1, match_id_column2, func.count().label("match_count"))
        .filter(Match.stadium_id == stadium_id)
        .group_by(match_id_column1, match_id_column2)
        .order_by(desc("match_count"))
        .all()
    )
    return matchups

def calculate_matches_played_in_stadium_class(db: Session, stadium_class_id: int):
    """Calculates the total matches played in a specific stadium class."""
    return db.query(func.count()).join(Stadium).filter(Stadium.stadium_class_id == stadium_class_id).scalar()

def calculate_win_percentage_by_stadium_class(db: Session, stadium_class_id: int, participant_type, participant_id):
    """Calculates the win percentage for a given participant in a specific stadium class."""
    if participant_type not in ("Player", "Combination"):
        return 0.0

    if participant_type == "Player":
        wins = db.query(func.count()).join(Stadium).filter(Stadium.stadium_class_id == stadium_class_id, Match.winner_id == participant_id).scalar()
        matches = db.query(func.count()).join(Stadium).filter(Stadium.stadium_class_id == stadium_class_id, or_(Match.player1_id == participant_id, Match.player2_id == participant_id)).scalar()
    elif participant_type == "Combination":
        wins = db.query(func.count()).join(Stadium).filter(Stadium.stadium_class_id == stadium_class_id, or_(
                and_(Match.combination1_id == participant_id, Match.player1_id == Match.winner_id),
                and_(Match.combination2_id == participant_id, Match.player2_id == Match.winner_id)
            )).scalar()
        matches = db.query(func.count()).join(Stadium).filter(Stadium.stadium_class_id == stadium_class_id, or_(Match.combination1_id == participant_id, Match.combination2_id == participant_id)).scalar()
    else:
        return 0.0

    if matches == 0:
        return 0.0
    return (wins / matches) * 100

def calculate_most_common_win_type_by_stadium_class(db: Session, stadium_class_id: int):
    """Calculates the most common win type in a specific stadium class."""
    most_common_win_type = (
        db.query(Match.finish_type)
        .join(Stadium)
        .filter(Stadium.stadium_class_id == stadium_class_id)
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_win_type[0] if most_common_win_type else None

def calculate_most_common_matchups_in_stadium_class(db: Session, stadium_class_id: int, participant_type):
    """Calculates the most common matchups in a specific stadium class."""
    if participant_type not in ("Player", "Combination"):
        return []

    match_id_column1 = Match.player1_id if participant_type == "Player" else Match.combination1_id
    match_id_column2 = Match.player2_id if participant_type == "Player" else Match.combination2_id

    matchups = (
        db.query(match_id_column1, match_id_column2, func.count().label("match_count"))
        .join(Stadium)
        .filter(Stadium.stadium_class_id == stadium_class_id)
        .group_by(match_id_column1, match_id_column2)
        .order_by(desc("match_count"))
        .all()
    )
    return matchups

# ... (Previous functions)

# --- Launcher Statistics Functions ---

def calculate_launcher_usage_frequency(db: Session, launcher_id: int):
    """Calculates how often a specific launcher is used."""
    return db.query(func.count()).filter(or_(Match.player1_launcher_id == launcher_id, Match.player2_launcher_id == launcher_id)).scalar()

def calculate_win_percentage_by_launcher(db: Session, launcher_id: int):
    """Calculates the win percentage for a given launcher."""
    wins = db.query(func.count()).filter(or_(
        and_(Match.player1_launcher_id == launcher_id, Match.player1_id == Match.winner_id),
        and_(Match.player2_launcher_id == launcher_id, Match.player2_id == Match.winner_id)
    )).scalar()
    matches = db.query(func.count()).filter(or_(Match.player1_launcher_id == launcher_id, Match.player2_launcher_id == launcher_id)).scalar()
    if matches == 0:
        return 0.0
    return (wins / matches) * 100

def calculate_most_common_win_type_by_launcher_class(db: Session, launcher_class_id: int):
    """Calculates the most common win type for a given launcher class."""
    most_common_win_type = (
        db.query(Match.finish_type)
        .join(Launcher)
        .filter(Launcher.launcher_class_id == launcher_class_id)
        .group_by(Match.finish_type)
        .order_by(desc(func.count(Match.finish_type)))
        .first()
    )
    return most_common_win_type[0] if most_common_win_type else None

# --- Matchups Statistics Functions ---

def calculate_head_to_head_record(db: Session, player1_id: int, player2_id: int):
    """Calculates the head-to-head record (wins, losses, draws) between two players."""
    player1_wins = db.query(func.count()).filter(Match.player1_id == player1_id, Match.winner_id == player1_id, Match.player2_id == player2_id).scalar()
    player2_wins = db.query(func.count()).filter(Match.player1_id == player1_id, Match.winner_id == player2_id, Match.player2_id == player2_id).scalar()
    draws = db.query(func.count()).filter(Match.player1_id == player1_id, Match.draw == True, Match.player2_id == player2_id).scalar()
    return player1_wins, player2_wins, draws

def calculate_head_to_head_win_percentage(db: Session, player1_id: int, player2_id: int):
    """Calculates the head-to-head win percentage for player1 against player2."""
    player1_wins, player2_wins, draws = calculate_head_to_head_record(db, player1_id, player2_id)
    total_matches = player1_wins + player2_wins + draws
    if total_matches == 0:
        return 0.0
    return (player1_wins / total_matches) * 100

def calculate_head_to_head_non_loss_percentage(db: Session, player1_id: int, player2_id: int):
    """Calculates the head-to-head non-loss percentage for player1 against player2."""
    player1_wins, player2_wins, draws = calculate_head_to_head_record(db, player1_id, player2_id)
    total_matches = player1_wins + player2_wins + draws
    if total_matches == 0:
        return 0.0
    return ((player1_wins + draws) / total_matches) * 100

# ... (Previous functions)

# --- Additional Statistics Functions ---

def calculate_finish_type_distribution(db: Session, participant_type, participant_id, stadium_id=None):
    """Calculates the distribution of finish types for a player, combination, or stadium."""
    if participant_type not in ("Player", "Combination", "Stadium"):
        return {}

    filters = []

    if participant_type == "Player":
        filters.append(or_(Match.player1_id == participant_id, Match.player2_id == participant_id))
        if participant_id is not None:
            filters.append(or_(
                and_(Match.player1_id == participant_id, Match.player1_id == Match.winner_id),
                and_(Match.player2_id == participant_id, Match.player2_id == Match.winner_id)
            ))
    elif participant_type == "Combination":
        filters.append(or_(Match.combination1_id == participant_id, Match.combination2_id == participant_id))
        if participant_id is not None:
            filters.append(or_(
                and_(Match.combination1_id == participant_id, Match.player1_id == Match.winner_id),
                and_(Match.combination2_id == participant_id, Match.player2_id == Match.winner_id)
            ))
    elif participant_type == "Stadium":
        filters.append(Match.stadium_id == participant_id)

    if stadium_id is not None:
        filters.append(Match.tournament_id == stadium_id)

    finish_types = (
        db.query(Match.finish_type, func.count())
        .filter(*filters)
        .group_by(Match.finish_type)
        .all()
    )
    return dict(finish_types)

def calculate_average_match_length(db: Session, tournament_id: int):
    """Calculates the average match length in a given tournament."""
    avg_match_length = (
        db.query(func.avg(cast((Match.end_time - Match.start_time), Float)))
        .filter(Match.tournament_id == tournament_id)
        .scalar()
    )
    if avg_match_length:
        return avg_match_length
    return None

def calculate_most_common_matchups(db: Session, participant_type):
    """Calculates the most common matchups between players or combinations."""
    if participant_type not in ("Player", "Combination"):
        return []

    match_id_column1 = Match.player1_id if participant_type == "Player" else Match.combination1_id
    match_id_column2 = Match.player2_id if participant_type == "Player" else Match.combination2_id

    matchups = (
        db.query(match_id_column1, match_id_column2, func.count().label("match_count"))
        .group_by(match_id_column1, match_id_column2)
        .order_by(desc("match_count"))
        .all()
    )
    return matchups

# --- Tournament Statistics Functions ---

def calculate_tournament_standings(db: Session, tournament_id: int, participant_type):
    """Calculates the tournament standings based on wins."""
    if participant_type not in ("Player", "Combination"):
        return []
    
    participant_id_column = Player.player_id if participant_type == "Player" else BeybladeCombination.combination_id
    participant_table = Player if participant_type == "Player" else BeybladeCombination
    participant_matches_table = Match

    standings = (
        db.query(
            participant_id_column,
            func.count(case((participant_matches_table.winner_id == participant_id_column, 1))).label("wins"),
            func.count().label("matches")
        )
        .join(TournamentParticipant, and_(TournamentParticipant.participant_id == participant_id_column, TournamentParticipant.participant_type == participant_type, TournamentParticipant.tournament_id == tournament_id))
        .join(participant_matches_table, or_(and_(participant_matches_table.player1_id == participant_id_column, participant_matches_table.tournament_id == tournament_id), and_(participant_matches_table.player2_id == participant_id_column, participant_matches_table.tournament_id == tournament_id)))
        .filter(TournamentParticipant.tournament_id == tournament_id)
        .group_by(participant_id_column)
        .order_by(desc("wins"))
        .all()
    )
    return standings

