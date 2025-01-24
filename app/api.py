import threading
import time
import json
from flask import Flask, jsonify, request, Blueprint
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_, case, func, desc, cast, Float

# Import from db.py
from db import SessionLocal, engine

# Import statistics module
from statistics import *

from app import publish_mqtt_message, MQTT_TOPIC_PREFIX, client, connected_flag

# Import models
from models import Player, BeybladeCombination, Tournament, Stadium, StadiumClass, Launcher, LauncherClass, Match, TournamentParticipant

# Define the Blueprint object
api = Blueprint('api', __name__)

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
    players_data = jsonify(player_list)
    publish_mqtt_message("beyblade/players", players_data)
    return players_data

@app.route("/api/part/<int:part_id>/usage_frequency")
def get_part_usage_frequency(part_id):
    usage_frequency = calculate_part_usage_frequency(part_id)
    data = jsonify({"usage_frequency": usage_frequency})
    publish_mqtt_message(f"beyblade/parts/{part_id}/usage_frequency", data)
    return data

@app.route("/api/part/<int:part_id>/win_rate")
def get_part_win_rate(part_id):
    win_rate = calculate_part_win_rate(part_id)
    data = jsonify({"win_rate": win_rate})
    publish_mqtt_message(f"beyblade/parts/{part_id}/win_rate", data)
    return data

@app.route("/api/part/<int:part_id>/most_common_combinations")
def get_part_most_common_combinations(part_id):
    common_combinations = calculate_most_common_combinations_with_part(part_id)
    data = jsonify({"most_common_combinations": common_combinations})
    publish_mqtt_message(f"beyblade/parts/{part_id}/most_common_combinations", data)
    return data

@app.route("/api/part/<int:part_id>/total_points")
def get_part_total_points(part_id):
    total_points = calculate_part_total_points(part_id)
    data = jsonify({"total_points": total_points})
    publish_mqtt_message(f"beyblade/parts/{part_id}/total_points", data)
    return data

@app.route("/api/part/<int:part_id>/average_points_per_match")
def get_part_average_points_per_match(part_id):
    average_points = calculate_part_average_points_per_match(part_id)
    data = jsonify({"average_points_per_match": average_points})
    publish_mqtt_message(f"beyblade/parts/{part_id}/average_points_per_match", data)
    return data

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
    player_stats = jsonify(stats)
    publish_mqtt_message(f"beyblade/players/{player_id}/stats", player_stats)
    return player_stats

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
    combinations_data = jsonify(combination_list)
    publish_mqtt_message("beyblade/combinations", combinations_data)
    return combinations_data


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
    combination_stats = jsonify(stats)
    publish_mqtt_message(f"beyblade/combinations/{combination_id}/stats", combination_stats)
    return combination_stats

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
    tournaments_data = jsonify(tournament_list)
    publish_mqtt_message("beyblade/tournaments", tournaments_data)
    return tournaments_data

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
    tournament_data_json = jsonify(tournament_data)
    publish_mqtt_message(f"beyblade/tournaments/{tournament_id}", tournament_data_json)
    return tournament_data_json

@app.route("/api/tournament/<int:tournament_id>/standings")
def get_tournament_standings(tournament_id):
    db = SessionLocal()
    tournament = db.query(Tournament).filter(Tournament.tournament_id == tournament_id).first()
    if not tournament:
        db.close()
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
    standings_json = jsonify({
        "tournament_id": tournament_id,
        "tournament_name": tournament.tournament_name,
        "tournament_type": tournament.tournament_type,
        "standings": standings_with_names
    })
    publish_mqtt_message(f"beyblade/tournaments/{tournament_id}/standings", standings_json)
    return standings_json

@app.route("/api/stadiums")
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
    stadiums_json = jsonify(stadium_list)
    publish_mqtt_message("beyblade/stadiums", stadiums_json)
    return stadiums_json

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
    stadium_json = jsonify(stadium_data)
    publish_mqtt_message(f"beyblade/stadiums/{stadium_id}", stadium_json)
    return stadium_json

@app.route("/api/stadium/<int:stadium_id>/matchups/<string:participant_type>")
def get_stadium_matchups(stadium_id, participant_type):
    db = SessionLocal()
    stadium = db.query(Stadium).filter(Stadium.stadium_id == stadium_id).first()
    if stadium is None:
        db.close()
        return jsonify({"error": "Stadium not found"}), 404

    matchups = calculate_most_common_matchups_in_stadium(stadium_id, participant_type)
    db.close()
    matchups_json = jsonify(matchups)
    publish_mqtt_message(f"beyblade/stadiums/{stadium_id}/matchups/{participant_type}", matchups_json)
    return matchups_json

@app.route("/api/stadium/<int:stadium_id>/finish_type_distribution")
def get_stadium_finish_type_distribution(stadium_id):
    db = SessionLocal()
    stadium = db.query(Stadium).filter(Stadium.stadium_id == stadium_id).first()
    if stadium is None:
        db.close()
        return jsonify({"error": "Stadium not found"}), 404

    distribution = calculate_finish_type_distribution("Stadium", stadium_id)
    db.close()
    distribution_json = jsonify(distribution)
    publish_mqtt_message(f"beyblade/stadiums/{stadium_id}/finish_type_distribution",distribution_json)
    return distribution_json

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
    stadium_classes_json = jsonify(stadium_class_list)
    publish_mqtt_message("beyblade/stadium_classes", stadium_classes_json)
    return stadium_classes_json

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
    stadium_class_json = jsonify(stadium_class_data)
    publish_mqtt_message(f"beyblade/stadium_classes/{stadium_class_id}", stadium_class_json)
    return stadium_class_json

@app.route("/api/stadium_class/<int:stadium_class_id>/matchups/<string:participant_type>")
def get_stadium_class_matchups(stadium_class_id, participant_type):
    db = SessionLocal()
    stadium_class = db.query(StadiumClass).filter(StadiumClass.id == stadium_class_id).first()
    if stadium_class is None:
        db.close()
        return jsonify({"error": "Stadium Class not found"}), 404

    matchups = calculate_most_common_matchups_in_stadium_class(stadium_class_id, participant_type)
    db.close()
    matchups_json = jsonify(matchups)
    publish_mqtt_message(f"beyblade/stadium_classes/{stadium_class_id}/matchups/{participant_type}", matchups_json)
    return matchups_json

@app.route("/api/stadium_class/<int:stadium_class_id>/finish_type_distribution")
def get_stadium_class_finish_type_distribution(stadium_class_id):
    db = SessionLocal()
    stadium_class = db.query(StadiumClass).filter(StadiumClass.id == stadium_class_id).first()
    if stadium_class is None:
        db.close()
        return jsonify({"error": "Stadium Class not found"}), 404

    distribution = calculate_finish_type_distribution("StadiumClass", stadium_class_id)
    db.close()
    distribution_json = jsonify(distribution)
    publish_mqtt_message(f"beyblade/stadium_classes/{stadium_class_id}/finish_type_distribution", distribution_json)
    return distribution_json

@app.route("/api/stadium/<int:stadium_id>/matches_played")
def get_matches_played_in_stadium(stadium_id):
    matches_played = calculate_matches_played_in_stadium(stadium_id)
    data_json = jsonify({"matches_played": matches_played})
    publish_mqtt_message(f"beyblade/stadiums/{stadium_id}/matches_played", data_json)
    return data_json

@app.route("/api/stadium/<int:stadium_id>/win_percentage/<string:participant_type>")
def get_win_percentage_by_stadium(stadium_id, participant_type):
    win_percentage = calculate_win_percentage_by_stadium(stadium_id, participant_type)
    data_json = jsonify({"win_percentage": win_percentage})
    publish_mqtt_message(f"beyblade/stadiums/{stadium_id}/win_percentage/{participant_type}", data_json)
    return data_json

@app.route("/api/stadium/<int:stadium_id>/most_common_win_type")
def get_most_common_win_type_by_stadium(stadium_id):
    most_common_win_type = calculate_most_common_win_type_by_stadium(stadium_id)
    data_json = jsonify({"most_common_win_type": most_common_win_type})
    publish_mqtt_message(f"beyblade/stadiums/{stadium_id}/most_common_win_type", data_json)
    return data_json

@app.route("/api/stadium_class/<int:stadium_class_id>/matches_played")
def get_matches_played_in_stadium_class(stadium_class_id):
    matches_played = calculate_matches_played_in_stadium_class(stadium_class_id)
    data_json = jsonify({"matches_played": matches_played})
    publish_mqtt_message(f"beyblade/stadium_classes/{stadium_class_id}/matches_played", data_json)
    return data_json

@app.route("/api/stadium_class/<int:stadium_class_id>/win_percentage/<string:participant_type>")
def get_win_percentage_by_stadium_class(stadium_class_id, participant_type):
    win_percentage = calculate_win_percentage_by_stadium_class(stadium_class_id, participant_type)
    data_json = jsonify({"win_percentage": win_percentage})
    publish_mqtt_message(f"beyblade/stadium_classes/{stadium_class_id}/win_percentage/{participant_type}", data_json)
    return data_json

@app.route("/api/stadium_class/<int:stadium_class_id>/most_common_win_type")
def get_most_common_win_type_by_stadium_class(stadium_class_id):
    most_common_win_type = calculate_most_common_win_type_by_stadium_class(stadium_class_id)
    data_json = jsonify({"most_common_win_type": most_common_win_type})
    publish_mqtt_message(f"beyblade/stadium_classes/{stadium_class_id}/most_common_win_type", data_json)
    return data_json

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
    launchers_json = jsonify(launcher_list)
    publish_mqtt_message("beyblade/launchers", launchers_json)
    return launchers_json

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
    launcher_stats_json = jsonify(stats)
    publish_mqtt_message(f"beyblade/launchers/{launcher_id}/stats", launcher_stats_json)
    return launcher_stats_json

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
    launcher_classes_json = jsonify(launcher_class_list)
    publish_mqtt_message("beyblade/launcher_classes", launcher_classes_json)
    return launcher_classes_json

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
    launcher_class_json = jsonify(launcher_class_data)
    publish_mqtt_message(f"beyblade/launcher_classes/{launcher_class_id}", launcher_class_json)
    return launcher_class_json

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
    match_json = jsonify(match_data)
    publish_mqtt_message(f"beyblade/matches/{match_id}", match_json)
    return match_json

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
    matches_json = jsonify(match_list)
    publish_mqtt_message(f"beyblade/tournaments/{tournament_id}/matches", matches_json)
    return matches_json

@app.route("/api/tournament/<int:tournament_id>/average_match_length")
def get_tournament_average_match_length(tournament_id):
    average_match_length = calculate_average_match_length(tournament_id)
    data_json = jsonify({"average_match_length": average_match_length})
    publish_mqtt_message(f"beyblade/tournaments/{tournament_id}/average_match_length", data_json)
    return data_json

@app.route("/api/matchups/<string:participant_type>")
def get_most_common_matchups(participant_type):
    matchups = calculate_most_common_matchups(participant_type)
    matchups_json = jsonify(matchups)
    publish_mqtt_message(f"beyblade/matchups/{participant_type}", matchups_json)
    return matchups_json

@app.route("/api/player/<int:player1_id>/matchup/<int:player2_id>")
def get_player_matchup(player1_id, player2_id):
    head_to_head = calculate_head_to_head_record(player1_id, player2_id)
    win_percentage = calculate_head_to_head_win_percentage(player1_id, player2_id)
    non_loss_percentage = calculate_head_to_head_non_loss_percentage(player1_id, player2_id)
    data = {
        "head_to_head": head_to_head,
        "win_percentage": win_percentage,
        "non_loss_percentage": non_loss_percentage
    }
    data_json = jsonify(data)
    publish_mqtt_message(f"beyblade/matchups/players/{player1_id}/{player2_id}", data_json)
    return data_json

@app.route("/api/finish_type_distribution/<string:participant_type>/<int:participant_id>")
def get_finish_type_distribution(participant_type, participant_id):
    distribution = calculate_finish_type_distribution(participant_type, participant_id)
    distribution_json = jsonify(distribution)
    publish_mqtt_message(f"beyblade/finish_types/{participant_type}/{participant_id}", distribution_json)
    return distribution_json

@app.route("/api/finish_type_distribution/stadium/<int:stadium_id>")
def get_stadium_finish_type_distribution(stadium_id):
    distribution = calculate_finish_type_distribution("Stadium", stadium_id)
    distribution_json = jsonify(distribution)
    publish_mqtt_message(f"beyblade/finish_types/stadiums/{stadium_id}", distribution_json)
    return distribution_json

def publish_all_statistics():
    db = SessionLocal()
    try:
        # Players
        players = db.query(Player).all()
        for player in players:
            stats = { # Recreate the stats dictionary from the API endpoint
                "player_id": player.player_id,
                "player_name": player.player_name,
                "matches_played": calculate_player_matches_played(player.player_id),
                "win_percentage": calculate_player_win_percentage(player.player_id),
                "wins": calculate_player_wins(player.player_id),
                "losses": calculate_player_losses(player.player_id),
                "draws": calculate_player_draws(player.player_id),
                "most_common_winning_finish_type": calculate_player_most_common_winning_finish_type(player.player_id),
                "win_streak": calculate_player_win_streak(player.player_id),
                "loss_streak": calculate_player_loss_streak(player.player_id),
                "total_points": calculate_player_total_points(player.player_id),
                "average_points_per_match": calculate_player_average_points_per_match(player.player_id),
                "elo_rating": calculate_player_elo_rating(player.player_id)
            }
            publish_mqtt_message(f"{MQTT_TOPIC_PREFIX}players/{player.player_id}/stats", jsonify(stats))

        # Combinations (Similar structure as Players)
        combinations = db.query(BeybladeCombination).all()
        for combination in combinations:
            stats = {
                "combination_id": combination.combination_id,
                "combination_name": combination.combination_name,
                "matches_played": calculate_combination_matches_played(combination.combination_id),
                "win_percentage": calculate_combination_win_percentage(combination.combination_id),
                "wins": calculate_combination_wins(combination.combination_id),
                "draws": calculate_combination_draws(combination.combination_id),
                "non_loss_percentage": calculate_combination_non_loss_percentage(combination.combination_id),
                "most_common_winning_finish_type": calculate_combination_most_common_winning_finish_type(combination.combination_id),
                "burst_rate": calculate_combination_burst_rate(combination.combination_id),
                "most_common_loss_type": calculate_combination_most_common_loss_type(combination.combination_id),
                "most_common_opponent": calculate_combination_most_common_opponent(combination.combination_id),
                "best_matchups": calculate_combination_best_matchups(combination.combination_id),
                "worst_matchups": calculate_combination_worst_matchups(combination.combination_id),
                "total_points": calculate_combination_total_points(combination.combination_id),
                "average_points_per_match": calculate_combination_average_points_per_match(combination.combination_id),
                "elo_rating": calculate_combination_elo_rating(combination.combination_id)
            }
            publish_mqtt_message(f"{MQTT_TOPIC_PREFIX}combinations/{combination.combination_id}/stats", jsonify(stats))

        #Stadiums
        stadiums = db.query(Stadium).all()
        for stadium in stadiums:
            data = {
                "matches_played": calculate_matches_played_in_stadium(stadium.stadium_id),
                "win_percentage_players": calculate_win_percentage_by_stadium(stadium.stadium_id, "Player"),
                "win_percentage_combinations": calculate_win_percentage_by_stadium(stadium.stadium_id, "Combination"),
                "most_common_win_type": calculate_most_common_win_type_by_stadium(stadium.stadium_id)
            }
            publish_mqtt_message(f"{MQTT_TOPIC_PREFIX}stadiums/{stadium.stadium_id}/stats", jsonify(data))
        
        #Stadium Classes
        stadium_classes = db.query(StadiumClass).all()
        for stadium_class in stadium_classes:
            data = {
                "matches_played": calculate_matches_played_in_stadium_class(stadium_class.id),
                "win_percentage_players": calculate_win_percentage_by_stadium_class(stadium_class.id, "Player"),
                "win_percentage_combinations": calculate_win_percentage_by_stadium_class(stadium_class.id, "Combination"),
                "most_common_win_type": calculate_most_common_win_type_by_stadium_class(stadium_class.id)
            }
            publish_mqtt_message(f"{MQTT_TOPIC_PREFIX}stadium_classes/{stadium_class.id}/stats", jsonify(data))

        #Launchers
        launchers = db.query(Launcher).all()
        for launcher in launchers:
            data = {
                "usage_frequency": calculate_launcher_usage_frequency(launcher.launcher_id),
                "win_percentage": calculate_win_percentage_by_launcher(launcher.launcher_id)
            }
            publish_mqtt_message(f"{MQTT_TOPIC_PREFIX}launchers/{launcher.launcher_id}/stats", jsonify(data))

        #Launcher Classes
        launcher_classes = db.query(LauncherClass).all()
        for launcher_class in launcher_classes:
            data = {
                "most_common_win_type": calculate_most_common_win_type_by_launcher_class(launcher_class.id)
            }
            publish_mqtt_message(f"{MQTT_TOPIC_PREFIX}launcher_classes/{launcher_class.id}/stats", jsonify(data))

    except Exception as e:
        logger.error(f"Error publishing statistics: {e}")
    finally:
        db.close()

def run_statistics_loop():
    while True:
        if client and connected_flag:
            logger.info("Publishing statistics...")
            publish_all_statistics()
            logger.info("Statistics published.")
        else:
            logger.error("MQTT Client not connected, skipping statistics publishing")
        time.sleep(15 * 60)  # Sleep for 15 minutes

def start_statistics_thread():
    statistics_thread = threading.Thread(target=run_statistics_loop)
    statistics_thread.daemon = True  # Allow the main program to exit even if the thread is running
    statistics_thread.start()