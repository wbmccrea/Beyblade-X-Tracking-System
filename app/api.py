from flask import Flask, jsonify, request
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_, case, func, desc, cast, Float

# Import from db.py
from db import SessionLocal, engine

# Import statistics module
from statistics import (
    calculate_player_matches_played,
    calculate_player_win_percentage,
    calculate_player_wins,
    calculate_player_losses,
    calculate_player_draws,
    calculate_player_most_common_winning_finish_type,
    calculate_player_win_streak,
    calculate_player_loss_streak,
    calculate_combination_matches_played,
    calculate_combination_win_percentage,
    calculate_combination_wins,
    calculate_combination_draws,
    calculate_combination_non_loss_percentage,
    calculate_combination_most_common_winning_finish_type,
    calculate_combination_burst_rate,
    calculate_combination_most_common_loss_type,
    calculate_combination_most_common_opponent,
    calculate_combination_best_matchups,
    calculate_combination_worst_matchups,
    calculate_combination_total_points,
    calculate_combination_average_points_per_match,
    calculate_combination_elo_rating,
    calculate_part_usage_frequency,
    calculate_part_win_rate,
    calculate_most_common_combinations_with_part,
    calculate_part_total_points,
    calculate_part_average_points_per_match,
    calculate_matches_played_in_stadium,
    calculate_win_percentage_by_stadium,
    calculate_most_common_win_type_by_stadium,
    calculate_most_common_matchups_in_stadium,
    calculate_matches_played_in_stadium_class,
    calculate_win_percentage_by_stadium_class,
    calculate_most_common_win_type_by_stadium_class,
    calculate_most_common_matchups_in_stadium_class,
    calculate_launcher_usage_frequency,
    calculate_win_percentage_by_launcher,
    calculate_most_common_win_type_by_launcher_class,
    calculate_head_to_head_record,
    calculate_head_to_head_win_percentage,
    calculate_head_to_head_non_loss_percentage,
    calculate_finish_type_distribution,
    calculate_average_match_length,
    calculate_most_common_matchups,
    calculate_tournament_standings,
)

# Import models
from models import Player, BeybladeCombination, Tournament, Stadium, StadiumClass, Launcher, LauncherClass, Match, TournamentParticipant

# Create Flask application instance
app = Flask(__name__)

@app.route("/api/players")
def get_players():
    db = SessionLocal()
    players = db.query(Player).all()
    player_list = []
    for player in players:
        player_list.append({
            "player_id": player.player_id,
            "player_name": player.player_name
        })
    db.close()
    return jsonify(player_list)

@app.route("/api/player/<int:player_id>")
def get_player(player_id):
    db = SessionLocal()
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if player is None:
        db.close()
        return jsonify({"error": "Player not found"}), 404

    stats = {
        "player_id": player.player_id,
        "player_name": player.player_name,
        "matches_played": calculate_player_matches_played(player_id),
        "win_percentage": calculate_player_win_percentage(player_id),
        "wins": calculate_player_wins(player_id),
        "losses": calculate_player_losses(player_id),
        "draws": calculate_player_draws(player_id),
        "most_common_winning_finish_type": calculate_player_most_common_winning_finish_type(player_id),
        "win_streak": calculate_player_win_streak(player_id),
        "loss_streak": calculate_player_loss_streak(player_id),
    }
    db.close()
    return jsonify(stats)

@app.route("/api/combinations")
def get_combinations():
    db = SessionLocal()
    combinations = db.query(BeybladeCombination).all()
    combination_list = []
    for combination in combinations:
        combination_list.append({
            "combination_id": combination.combination_id,
            "combination_name": combination.combination_name
        })
    db.close()
    return jsonify(combination_list)


@app.route("/api/combination/<int:combination_id>")
def get_combination(combination_id):
    db = SessionLocal()
    combination = db.query(BeybladeCombination).filter(BeybladeCombination.combination_id == combination_id).first()
    if combination is None:
        db.close()
        return jsonify({"error": "Combination not found"}), 404

    stats = {
        "combination_id": combination.combination_id,
        "combination_name": combination.combination_name,
        "matches_played": calculate_combination_matches_played(combination_id),
        "win_percentage": calculate_combination_win_percentage(combination_id),
        "wins": calculate_combination_wins(combination_id),
        "draws": calculate_combination_draws(combination_id),
        "non_loss_percentage": calculate_combination_non_loss_percentage(combination_id),
        "most_common_winning_finish_type": calculate_combination_most_common_winning_finish_type(combination_id),
        "burst_rate": calculate_combination_burst_rate(combination_id),
        "most_common_loss_type": calculate_combination_most_common_loss_type(combination_id),
        "most_common_opponent": calculate_combination_most_common_opponent(combination_id),
        "best_matchups": calculate_combination_best_matchups(combination_id),
        "worst_matchups": calculate_combination_worst_matchups(combination_id),
        "total_points": calculate_combination_total_points(combination_id),
        "average_points_per_match": calculate_combination_average_points_per_match(combination_id),
        "elo_rating": calculate_combination_elo_rating(combination_id)

    }
    db.close()
    return jsonify(stats)

@app.route("/api/tournaments")
def get_tournaments():
    db = SessionLocal()
    tournaments = db.query(Tournament).all()
    tournament_list = []
    for tournament in tournaments:
        tournament_list.append({
            "tournament_id": tournament.tournament_id,
            "tournament_name": tournament.tournament_name,
            "start_date": tournament.start_date.isoformat() if tournament.start_date else None,
            "end_date": tournament.end_date.isoformat() if tournament.end_date else None,
            "tournament_type": tournament.tournament_type
        })
    db.close()
    return jsonify(tournament_list)

@app.route("/api/tournament/<int:tournament_id>")
def get_tournament(tournament_id):
    db = SessionLocal()
    tournament = db.query(Tournament).filter(Tournament.tournament_id == tournament_id).first()
    if tournament is None:
        db.close()
        return jsonify({"error": "Tournament not found"}), 404

    tournament_data = {
        "tournament_id": tournament.tournament_id,
        "tournament_name": tournament.tournament_name,
        "start_date": tournament.start_date.isoformat() if tournament.start_date else None,
        "end_date": tournament.end_date.isoformat() if tournament.end_date else None,
        "tournament_type": tournament.tournament_type
    }
    db.close()
    return jsonify(tournament_data)

@app.route("/api/tournament/<int:tournament_id>/standings")
def get_tournament_standings(tournament_id):
    db = SessionLocal()
    tournament = db.query(Tournament).filter(Tournament.tournament_id == tournament_id).first()
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404

    participant_type = "Player" if tournament.tournament_type in ("Standard", "PlayerLadder") else "Combination"
    standings = calculate_tournament_standings(tournament_id, participant_type)

    standings_with_names = []
    for participant in standings:
        participant_data = {}
        if participant_type == "Player":
            player = db.query(Player).filter(Player.player_id == participant[0]).first()
            participant_data["participant_name"] = player.player_name if player else None
        else:
            combination = db.query(BeybladeCombination).filter(BeybladeCombination.combination_id == participant[0]).first()
            participant_data["participant_name"] = combination.combination_name if combination else None
        participant_data["participant_id"] = participant[0]
        participant_data["wins"] = participant[1]
        participant_data["matches"] = participant[2]
        standings_with_names.append(participant_data)

    db.close()
    return jsonify({
        "tournament_id": tournament_id,
        "tournament_name": tournament.tournament_name,
        "tournament_type": tournament.tournament_type,
        "standings": standings_with_names
    })

app.route("/api/stadiums")
def get_stadiums():
    db = SessionLocal()
    stadiums = db.query(Stadium).all()
    stadium_list = []
    for stadium in stadiums:
        stadium_list.append({
            "stadium_id": stadium.stadium_id,
            "stadium_name": stadium.stadium_name,
            "stadium_class": stadium.stadium_class
        })
    db.close()
    return jsonify(stadium_list)

@app.route("/api/stadium/<int:stadium_id>")
def get_stadium(stadium_id):
    db = SessionLocal()
    stadium = db.query(Stadium).filter(Stadium.stadium_id == stadium_id).first()
    if stadium is None:
        db.close()
        return jsonify({"error": "Stadium not found"}), 404

    stadium_data = {
        "stadium_id": stadium.stadium_id,
        "stadium_name": stadium.stadium_name,
        "stadium_class": stadium.stadium_class
    }
    db.close()
    return jsonify(stadium_data)

@app.route("/api/stadium/<int:stadium_id>/matchups/<string:participant_type>")
def get_stadium_matchups(stadium_id, participant_type):
    db = SessionLocal()
    stadium = db.query(Stadium).filter(Stadium.stadium_id == stadium_id).first()
    if stadium is None:
        db.close()
        return jsonify({"error": "Stadium not found"}), 404

    matchups = calculate_most_common_matchups_in_stadium(stadium_id, participant_type)
    db.close()
    return jsonify(matchups)

@app.route("/api/stadium/<int:stadium_id>/finish_type_distribution")
def get_stadium_finish_type_distribution(stadium_id):
    db = SessionLocal()
    stadium = db.query(Stadium).filter(Stadium.stadium_id == stadium_id).first()
    if stadium is None:
        db.close()
        return jsonify({"error": "Stadium not found"}), 404

    distribution = calculate_finish_type_distribution("Stadium", stadium_id)
    db.close()
    return jsonify(distribution)

@app.route("/api/stadium_classes")
def get_stadium_classes():
    db = SessionLocal()
    stadium_classes = db.query(StadiumClass).all()
    stadium_class_list = []
    for stadium_class in stadium_classes:
        stadium_class_list.append({
            "stadium_class_id": stadium_class.id,
            "stadium_class_name": stadium_class.name,
            "stadium_class_description": stadium_class.description
        })
    db.close()
    return jsonify(stadium_class_list)

@app.route("/api/stadium_class/<int:stadium_class_id>")
def get_stadium_class(stadium_class_id):
    db = SessionLocal()
    stadium_class = db.query(StadiumClass).filter(StadiumClass.id == stadium_class_id).first()
    if stadium_class is None:
        db.close()
        return jsonify({"error": "Stadium Class not found"}), 404

    stadium_class_data = {
        "stadium_class_id": stadium_class.id,
        "stadium_class_name": stadium_class.name,
        "stadium_class_description": stadium_class.description
    }
    db.close()
    return jsonify(stadium_class_data)

@app.route("/api/stadium_class/<int:stadium_class_id>/matchups/<string:participant_type>")
def get_stadium_class_matchups(stadium_class_id, participant_type):
    db = SessionLocal()
    stadium_class = db.query(StadiumClass).filter(StadiumClass.id == stadium_class_id).first()
    if stadium_class is None:
        db.close()
        return jsonify({"error": "Stadium Class not found"}), 404

    matchups = calculate_most_common_matchups_in_stadium_class(stadium_class_id, participant_type)
    db.close()
    return jsonify(matchups)

@app.route("/api/stadium_class/<int:stadium_class_id>/finish_type_distribution")
def get_stadium_class_finish_type_distribution(stadium_class_id):
    db = SessionLocal()
    stadium_class = db.query(StadiumClass).filter(StadiumClass.id == stadium_class_id).first()
    if stadium_class is None:
        db.close()
        return jsonify({"error": "Stadium Class not found"}), 404

    distribution = calculate_finish_type_distribution("StadiumClass", stadium_class_id)
    db.close()
    return jsonify(distribution)

@app.route("/api/launchers")
def get_launchers():
    db = SessionLocal()
    launchers = db.query(Launcher).all()
    launcher_list = []
    for launcher in launchers:
        launcher_list.append({
            "launcher_id": launcher.launcher_id,
            "launcher_name": launcher.launcher_name,
            "launcher_class_id": launcher.launcher_class_id
        })
    db.close()
    return jsonify(launcher_list)

@app.route("/api/launcher/<int:launcher_id>")
def get_launcher(launcher_id):
    db = SessionLocal()
    launcher = db.query(Launcher).filter(Launcher.launcher_id == launcher_id).first()
    if launcher is None:
        db.close()
        return jsonify({"error": "Launcher not found"}), 404

    stats = {
        "launcher_id": launcher.launcher_id,
        "launcher_name": launcher.launcher_name,
        "launcher_class_id": launcher.launcher_class_id,
        "usage_frequency": calculate_launcher_usage_frequency(launcher_id),
        "win_percentage": calculate_win_percentage_by_launcher(launcher_id),
    }
    db.close()
    return jsonify(stats)

@app.route("/api/launcher_classes")
def get_launcher_classes():
    db = SessionLocal()
    launcher_classes = db.query(LauncherClass).all()
    launcher_class_list = []
    for launcher_class in launcher_classes:
        launcher_class_list.append({
            "launcher_class_id": launcher_class.id,
            "launcher_class_name": launcher_class.name,
            "launcher_class_description": launcher_class.description
        })
    db.close()
    return jsonify(launcher_class_list)

@app.route("/api/launcher_class/<int:launcher_class_id>")
def get_launcher_class(launcher_class_id):
    db = SessionLocal()
    launcher_class = db.query(LauncherClass).filter(LauncherClass.id == launcher_class_id).first()
    if launcher_class is None:
        db.close()
        return jsonify({"error": "Launcher Class not found"}), 404

    launcher_class_data = {
        "launcher_class_id": launcher_class.id,
        "launcher_class_name": launcher_class.name,
        "launcher_class_description": launcher_class.description,
        "most_common_win_type": calculate_most_common_win_type_by_launcher_class(launcher_class_id)
    }
    db.close()
    return jsonify(launcher_class_data)

@app.route("/api/match/<int:match_id>")
def get_match(match_id):
    db = SessionLocal()
    match = db.query(Match).filter(Match.match_id == match_id).first()
    if match is None:
        db.close()
        return jsonify({"error": "Match not found"}), 404

    match_data = {
        "match_id": match.match_id,
        "tournament_id": match.tournament_id,
        "player1_id": match.player1_id,
        "player2_id": match.player2_id,
        "combination1_id": match.combination1_id,
        "combination2_id": match.combination2_id,
        "player1_launcher_id": match.player1_launcher_id,
        "player2_launcher_id": match.player2_launcher_id,
        "stadium_id": match.stadium_id,
        "winner_id": match.winner_id,
        "finish_type": match.finish_type,
        "start_time": match.start_time.isoformat() if match.start_time else None,
        "end_time": match.end_time.isoformat() if match.end_time else None,
        "draw": match.draw
    }
    db.close()
    return jsonify(match_data)

@app.route("/api/tournament/<int:tournament_id>/matches")
def get_tournament_matches(tournament_id):
    db = SessionLocal()
    matches = db.query(Match).filter(Match.tournament_id == tournament_id).all()
    match_list = []
    for match in matches:
        match_list.append({
            "match_id": match.match_id,
            "tournament_id": match.tournament_id,
            "player1_id": match.player1_id,
            "player2_id": match.player2_id,
            "combination1_id": match.combination1_id,
            "combination2_id": match.combination2_id,
            "player1_launcher_id": match.player1_launcher_id,
            "player2_launcher_id": match.player2_launcher_id,
            "stadium_id": match.stadium_id,
            "winner_id": match.winner_id,
            "finish_type": match.finish_type,
            "start_time": match.start_time.isoformat() if match.start_time else None,
            "end_time": match.end_time.isoformat() if match.end_time else None,
            "draw": match.draw
        })
    db.close()
    return jsonify(match_list)

@app.route("/api/tournament/<int:tournament_id>/average_match_length")
def get_tournament_average_match_length(tournament_id):
    db = SessionLocal()
    average_match_length = calculate_average_match_length(tournament_id)
    db.close()
    return jsonify({"average_match_length": average_match_length})

@app.route("/api/matchups/<string:participant_type>")
def get_most_common_matchups(participant_type):
    db = SessionLocal()
    matchups = calculate_most_common_matchups(participant_type)
    db.close()
    return jsonify(matchups)

@app.route("/api/player/<int:player1_id>/matchup/<int:player2_id>")
def get_player_matchup(player1_id, player2_id):
    db = SessionLocal()
    head_to_head = calculate_head_to_head_record(player1_id, player2_id)
    win_percentage = calculate_head_to_head_win_percentage(player1_id, player2_id)
    non_loss_percentage = calculate_head_to_head_non_loss_percentage(player1_id, player2_id)
    db.close()
    return jsonify({
        "head_to_head": head_to_head,
        "win_percentage": win_percentage,
        "non_loss_percentage": non_loss_percentage
    })

@app.route("/api/finish_type_distribution/<string:participant_type>/<int:participant_id>")
def get_finish_type_distribution(participant_type, participant_id):
    db = SessionLocal()
    distribution = calculate_finish_type_distribution(participant_type, participant_id)
    db.close()
    return jsonify(distribution)

@app.route("/api/finish_type_distribution/stadium/<int:stadium_id>")
def get_stadium_finish_type_distribution(stadium_id):
    db = SessionLocal()
    distribution = calculate_finish_type_distribution("Stadium", stadium_id)
    db.close()
    return jsonify(distribution)

