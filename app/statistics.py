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

# --- Player Statistics Functions ---

def calculate_player_matches_played(db: Session, player_id: int):
    """Calculates the total matches played by a player."""
    return (
        db.query(func.count())
        .select_from(Match)
        .filter(or_(Match.player1_id == player_id, Match.player2_id == player_id))
        .scalar()
    )


def calculate_player_wins(db: Session, player_id: int):
    """Calculates the total wins for a player."""
    return (
        db.query(func.count())
        .select_from(Match)
        .filter(
            or_(Match.player1_id == player_id, Match.player2_id == player_id),
            Match.winner_id == player_id,
        )
        .scalar()
    )


def calculate_player_win_rate(db: Session, player_id: int):
    """Calculates the win rate for a player (wins / total matches played)."""
    matches_played = calculate_player_matches_played(db, player_id)
    if matches_played == 0:
        return 0.0  # Avoid division by zero
    return calculate_player_wins(db, player_id) / matches_played


def calculate_player_average_opponent_elo(db: Session, player_id: int, tournament_id=None):
    """Calculates the average ELO rating of a player's opponents across all matches (or within a specific tournament)."""
    opponent_elo_query = (
        db.query(func.avg(case(Match.winner_id == player_id, then=Match.player2_elo_rating, else=Match.player1_elo_rating)))
        .select_from(Match)
        .filter(or_(Match.player1_id == player_id, Match.player2_id == player_id))
    )
    if tournament_id:
        opponent_elo_query = opponent_elo_query.filter(Match.tournament_id == tournament_id)
    return opponent_elo_query.scalar() if opponent_elo_query.scalar() is not None else 0.0  # Handle potential None value

# --- Combination Statistics Functions ---

def calculate_combination_matches_played(db: Session, combination_id: int):
    """Calculates the total matches played by a combination."""
    return (
        db.query(func.count())
        .select_from(Match)
        .filter(or_(Match.combination1_id == combination_id, Match.combination2_id == combination_id))
        .scalar()
    )


def calculate_combination_wins(db: Session, combination_id: int):
    """Calculates the total wins for a combination."""
    return (
        db.query(func.count())
        .select_from(Match)
        .filter(
            or_(Match.combination1_id == combination_id, Match.combination2_id == combination_id),
            Match.winner_id == combination_id,
        )
        .scalar()
    )

# ... (Previous Player and Combination Statistics functions)

def calculate_combination_loss_rate(db: Session, combination_id: int):
    """Calculates the loss rate for a combination (losses / total matches played)."""
    matches_played = calculate_combination_matches_played(db, combination_id)
    if matches_played == 0:
        return 0.0  # Avoid division by zero
    losses = calculate_combination_matches_played(db, combination_id) - calculate_combination_wins(db, combination_id)
    return losses / matches_played

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
        .select_from(Match)
        .filter(or_(
            and_(Match.combination1_id == combination_id, Match.player1_id == Match.winner_id, Match.finish_type == "Burst"),
            and_(Match.combination2_id == combination_id, Match.player2_id == Match.winner_id, Match.finish_type == "Burst")
        ))
        .scalar()
    )
    return (burst_wins / wins) * 100

# --- Beyblade Part Statistics Functions (Blade, Ratchet, Bit) ---

def calculate_part_usage_frequency(db: Session, part_type: str, part_id: int):
    """Calculates the usage frequency of a Beyblade part (Blade, Ratchet, Bit)."""
    if part_type == "Blade":
        return db.query(func.count()).select_from(BeybladeCombination).filter(BeybladeCombination.blade_id == part_id).scalar()
    elif part_type == "Ratchet":
        return db.query(func.count()).select_from(BeybladeCombination).filter(BeybladeCombination.ratchet_id == part_id).scalar()
    elif part_type == "Bit":
        return db.query(func.count()).select_from(BeybladeCombination).filter(BeybladeCombination.bit_id == part_id).scalar()
    else:
        return 0
    
# ... (Previous functions)

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

    if not combinations:  # Handle case where part is not used in any combinations
        return 0.0

    total_wins = 0
    for combination_id_tuple in combinations:
        combination_id = combination_id_tuple[0]
        total_wins += calculate_combination_wins(db, combination_id)
    
    total_matches = 0
    for combination_id_tuple in combinations:
        combination_id = combination_id_tuple[0]
        total_matches += calculate_combination_matches_played(db, combination_id)

    if total_matches == 0:
        return 0.0

    return (total_wins / total_matches) * 100

def calculate_most_common_combinations_with_part(db: Session, part_type: str, part_id: int):
    """Calculates the most common combinations that include a specific part."""
    if part_type == "Blade":
        return (
            db.query(BeybladeCombination)
            .filter(BeybladeCombination.blade_id == part_id)
            .all()
        )
    elif part_type == "Ratchet":
        return (
            db.query(BeybladeCombination)
            .filter(BeybladeCombination.ratchet_id == part_id)
            .all()
        )
    elif part_type == "Bit":
        return (
            db.query(BeybladeCombination)
            .filter(BeybladeCombination.bit_id == part_id)
            .all()
        )
    else:
        return []

# --- Stadium Statistics Functions ---

def calculate_matches_played_in_stadium(db: Session, stadium_id: int):
    """Calculates the total matches played in a specific stadium."""
    return db.query(func.count()).select_from(Match).filter(Match.stadium_id == stadium_id).scalar()

# ... (Previous functions)

def calculate_win_percentage_by_stadium(db: Session, stadium_id: int, participant_type, participant_id):
    """Calculates the win percentage for a given participant (player or combination) in a specific stadium."""
    if participant_type not in ("Player", "Combination"):
        return 0.0

    if participant_type == "Player":
        wins = db.query(func.count()).filter(Match.stadium_id == stadium_id, Match.winner_id == participant_id).scalar()
        matches = db.query(func.count()).filter(Match.stadium_id == stadium_id, or_(Match.player1_id == participant_id, Match.player2_id == participant_id)).scalar()
    else:  # Combination
        wins = db.query(func.count()).filter(Match.stadium_id == stadium_id, or_(
                and_(Match.combination1_id == participant_id, Match.player1_id == Match.winner_id),
                and_(Match.combination2_id == participant_id, Match.player2_id == Match.winner_id)
            )).scalar()
        matches = db.query(func.count()).filter(Match.stadium_id == stadium_id, or_(Match.combination1_id == participant_id, Match.combination2_id == participant_id)).scalar()

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

def calculate_most_common_matchups_in_stadium(db: Session, stadium_id: int):
    """Calculates the most common matchups in a specific stadium."""
    matchups = (
        db.query(Match.player1_id, Match.player2_id, func.count().label("match_count"))
        .filter(Match.stadium_id == stadium_id)
        .group_by(Match.player1_id, Match.player2_id)
        .order_by(desc("match_count"))
        .all()
    )
    return matchups

# --- Launcher Statistics Functions ---

def calculate_launcher_usage_frequency(db: Session, launcher_id: int):
    """Calculates how often a specific launcher is used."""
    return db.query(func.count()).filter(or_(Match.player1_launcher_id == launcher_id, Match.player2_launcher_id == launcher_id)).scalar()

def calculate_win_percentage_by_launcher(db: Session, launcher_id: int):
    """Calculates the win percentage for a given launcher."""
    wins = db.query(func.count()).filter(or_(and_(Match.player1_launcher_id == launcher_id, Match.player1_id == Match.winner_id), and_(Match.player2_launcher_id == launcher_id, Match.player2_id == Match.winner_id))).scalar()
    matches = db.query(func.count()).filter(or_(Match.player1_launcher_id == launcher_id, Match.player2_launcher_id == launcher_id)).scalar()
    if matches == 0:
        return 0
    return (wins / matches) * 100

# ... (Previous functions)

def calculate_most_common_win_type_by_launcher_class(db: Session, launcher_class_id: int):
    """Calculates the most common win type for a given launcher class."""
    most_common_win_type = (
        db.query(Match.finish_type)
        .join(Launcher, or_(Match.player1_launcher_id == Launcher.launcher_id, Match.player2_launcher_id == Launcher.launcher_id))
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

# --- Additional Statistics Functions ---

def calculate_finish_type_distribution(db: Session, participant_type, participant_id):
    """Calculates the distribution of finish types for a player or combination."""
    if participant_type not in ("Player", "Combination"):
        return {}

    filters = []
    if participant_type == "Player":
        filters.append(or_(Match.player1_id == participant_id, Match.player2_id == participant_id))
        if Match.player1_id == participant_id:
            filters.append(Match.player1_id == Match.winner_id)
        else:
            filters.append(Match.player2_id == Match.winner_id)
    else:
        filters.append(or_(Match.combination1_id == participant_id, Match.combination2_id == participant_id))
        if Match.combination1_id == participant_id:
            filters.append(Match.player1_id == Match.winner_id)
        else:
            filters.append(Match.player2_id == Match.winner_id)

    finish_types = (
        db.query(Match.finish_type, func.count())
        .filter(*filters)
        .group_by(Match.finish_type)
        .all()
    )
    return dict(finish_types)

# ... (Previous functions)

def calculate_average_match_length(db: Session, match_id: int):
    """Calculates the average match length (if start and end times are available)."""
    match = db.query(Match).filter(Match.match_id == match_id).first()
    if match and match.start_time and match.end_time:
        time_difference = match.end_time - match.start_time
        return time_difference.total_seconds()
    return None

def calculate_most_common_matchups(db: Session, participant_type):
    """Calculates the most common matchups between players or combinations."""
    if participant_type not in ("Player", "Combination"):
        return []
    
    table = Player if participant_type == "Player" else BeybladeCombination
    id_column = table.player_id if participant_type == "Player" else table.combination_id
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
        .join(TournamentParticipant, and_(TournamentParticipant.participant_id == participant_id_column, TournamentParticipant.participant_type == participant_type))
        .join(participant_matches_table, or_(and_(participant_matches_table.player1_id == participant_id_column, participant_matches_table.tournament_id == tournament_id), and_(participant_matches_table.player2_id == participant_id_column, participant_matches_table.tournament_id == tournament_id)))
        .filter(TournamentParticipant.tournament_id == tournament_id)
        .group_by(participant_id_column)
        .order_by(desc("wins"))
        .all()
    )
    return standings

