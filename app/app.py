global client  # Declare client as global at the beginning

import os
from dotenv import load_dotenv
import mysql.connector
from flask import Flask, jsonify, request, render_template, redirect, url_for, g
from datetime import datetime
from urllib.parse import unquote
import logging
from collections import Counter
import operator
import paho.mqtt.client as mqtt
import json
import time
import threading


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logger = logging.getLogger(__name__) #get a logger object


app = Flask(__name__)

#Database info
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# MQTT Configuration (from .env file)
MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.environ.get("MQTT_USER")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
MQTT_TOPIC_PREFIX = "beyblade/stats/"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return conn
    except mysql.connector.Error as e:
        logger.debug(f"Database connection error: {e}")
        return None

client = None  # Global client variable initialized to None
connected_flag = False

def on_connect(client, userdata, flags, rc):  # Move to global scope
    global connected_flag
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        connected_flag = True
    else:
        logger.error(f"Failed to connect to MQTT, return code {rc}")

def on_disconnect(client, userdata, rc):  # Move to global scope
    global connected_flag
    connected_flag = False
    if rc != 0:
        logger.error(f"Disconnected from MQTT Broker with code {rc}. Attempting to reconnect...")
        time.sleep(5)  # Wait before retrying
        connect_mqtt()

def connect_mqtt():
    global client # This is needed to modify the global client variable
    if client is None:  # Correct check: if client is None
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        try:
            client.connect(MQTT_BROKER, MQTT_PORT)
            return client
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return None
    return client # Return the client whether it's new or existing

def mqtt_loop():
    global client
    while True:
        if client:
            client.loop(timeout=0.1)  # Process MQTT events with a timeout
        time.sleep(0.01)   

def publish_stats():
    global connected_flag
    logger.info("publish_stats() called")
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Database connection error during stats publishing")
            return

        cursor = conn.cursor()

        player_stats = []
        cursor.execute("SELECT player_id, player_name FROM Players")
        players = cursor.fetchall()
        for player_id, player_name in players:
            cursor.execute("""
                SELECT
                    COUNT(CASE WHEN winner_id = %s THEN 1 END) AS wins,
                    COUNT(CASE WHEN (player1_id = %s OR player2_id = %s) AND winner_id IS NOT NULL AND winner_id != %s THEN 1 END) AS losses,
                    COUNT(CASE WHEN (player1_id = %s OR player2_id = %s) AND draw = 1 THEN 1 END) AS draws,
                    SUM(CASE
                        WHEN winner_id = %s AND finish_type = 'Survivor' THEN 1
                        WHEN winner_id = %s AND finish_type = 'KO' THEN 2
                        WHEN winner_id = %s AND finish_type = 'Burst' THEN 2
                        WHEN winner_id = %s AND finish_type = 'Extreme' THEN 3
                        ELSE 0
                    END) AS points
                FROM Matches
                WHERE player1_id = %s OR player2_id = %s;
            """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
            result = cursor.fetchone()
            wins, losses, draws, points = result or (0, 0, 0, 0)  # Handle potential None result
            player_stats.append({
                "name": player_name,
                "wins": wins, "losses": losses, "draws": draws, "points": int(points),
                "win_rate": (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0, #Win Rate
                "non_loss_rate": ((wins + draws) / (wins + losses + draws)) * 100 if (wins + losses + draws) > 0 else 0, #Non-loss Rate
            })

         # Recent Matches
        recent_matches = []
        cursor.execute("SELECT * FROM Matches ORDER BY match_time DESC LIMIT 5")
        matches = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        for match in matches:
            match_dict = dict(zip(column_names, match))
            # Convert datetime object to string
            if "match_time" in match_dict and match_dict["match_time"] is not None:
                match_dict["match_time"] = match_dict["match_time"].isoformat()
            recent_matches.append(match_dict)

        # Combination Stats
        combination_stats = []
        cursor.execute("SELECT combination_id, combination_name FROM BeybladeCombinations")
        combinations = cursor.fetchall()
        for combination_id, combination_name in combinations:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT m.match_id) AS matches_played,
                    COUNT(CASE WHEN m.player1_combination_id = %s AND m.winner_id = m.player1_id THEN 1 WHEN m.player2_combination_id = %s AND m.winner_id = m.player2_id THEN 1 END) AS wins,
                    SUM(CASE
                        WHEN m.player1_combination_id = %s AND m.winner_id = m.player1_id AND m.finish_type = 'Survivor' THEN 1
                        WHEN m.player1_combination_id = %s AND m.winner_id = m.player1_id AND m.finish_type = 'KO' THEN 2
                        WHEN m.player1_combination_id = %s AND m.winner_id = m.player1_id AND m.finish_type = 'Burst' THEN 2
                        WHEN m.player1_combination_id = %s AND m.winner_id = m.player1_id AND m.finish_type = 'Extreme' THEN 3
                        WHEN m.player2_combination_id = %s AND m.winner_id = m.player2_id AND m.finish_type = 'Survivor' THEN 1
                        WHEN m.player2_combination_id = %s AND m.winner_id = m.player2_id AND m.finish_type = 'KO' THEN 2
                        WHEN m.player2_combination_id = %s AND m.winner_id = m.player2_id AND m.finish_type = 'Burst' THEN 2
                        WHEN m.player2_combination_id = %s AND m.winner_id = m.player2_id AND m.finish_type = 'Extreme' THEN 3
                        ELSE 0
                    END) AS points
                FROM BeybladeCombinations bc
                LEFT JOIN Matches m ON bc.combination_id = m.player1_combination_id OR bc.combination_id = m.player2_combination_id
                WHERE bc.combination_id = %s
            """, (combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id, combination_id)) #14 parameters
            result = cursor.fetchone()
            matches_played, wins, points = result or (0, 0, 0)
            combination_stats.append({
                "name": combination_name,
                "matches_played": matches_played,
                "wins": wins,
                "points": int(points),
                "win_rate": (wins / matches_played) * 100 if matches_played > 0 else 0,
                "non_loss_rate": ((wins + (matches_played - wins)) / matches_played) * 100 if matches_played > 0 else 0,
            })

        # Convert data to JSON format

        player_stats_json = json.dumps(player_stats)
        recent_matches_json = json.dumps(recent_matches)
        combination_stats_json = json.dumps(combination_stats)

        logger.info(f"Publishing player stats: {player_stats_json}")
        logger.info(f"Publishing recent matches: {recent_matches_json}")
        logger.info(f"Publishing combination stats: {combination_stats_json}")

        client = g.mqtt_client  

        if client and connected_flag:  # Check the flag!
            # Publish player stats (unchanged)
            logger.info(f"Publishing to topic: {MQTT_TOPIC_PREFIX + 'player_stats'}")
            ret = client.publish(MQTT_TOPIC_PREFIX + "player_stats", player_stats_json)
            logger.info(f"Publish result for player stats: {ret}")  # Check return value

            # Publish recent matches (unchanged)
            logger.info(f"Publishing to topic: {MQTT_TOPIC_PREFIX + 'recent_matches'}")
            ret = client.publish(MQTT_TOPIC_PREFIX + "recent_matches", recent_matches_json)
            logger.info(f"Publish result for recent matches: {ret}")  # Check return value

            # **New: Publish combination stats**
            logger.info(f"Publishing to topic: {MQTT_TOPIC_PREFIX + 'combination_stats'}")
            ret = client.publish(MQTT_TOPIC_PREFIX + "combination_stats", combination_stats_json)  # Typo corrected: "recent_matches" should be "combination_stats"
            logger.info(f"Publish result for combination stats: {ret}")

        else:
            logger.error("MQTT client not connected, cannot publish stats")

        conn.close()
        logger.info("Stats published to MQTT (if successful)")

    except Exception as e:
        logger.error(f"Error publishing stats to MQTT: {e}")

@app.before_request
def before_request():
    g.mqtt_client = client


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'mqtt_client'):
        g.mqtt_client = None

# Start MQTT loop in a separate thread when the app starts
client = connect_mqtt()
if client:
    mqtt_thread = threading.Thread(target=mqtt_loop)
    mqtt_thread.daemon = True
    mqtt_thread.start()
else:
    logger.error("Failed to establish initial MQTT connection")

def publish_stats_at_startup():
    logger.info("Publishing stats at startup")
    if client:  # Check if MQTT client is connected
        publish_stats()

def get_id_by_name(table, name, id_column):
    conn = get_db_connection()
    if conn is None:
        logger.error("get_id_by_name: Database connection failed")
        return None
    cursor = conn.cursor()
    try:
        name = name.strip()
        #logger.info(f"get_id_by_name: Looking for '{name}' in table '{table}'")

        if table == "Players":
            name_column = "player_name"
        elif table == "BeybladeCombinations":
            name_column = "combination_name"
        elif table == "LauncherTypes":
            name_column = "launcher_name"
        elif table == "Stadiums":  # Add this case for Stadiums
            name_column = "stadium_name"  # Set name_column to "stadium_name"
        elif table == "Tournaments":  # Add this elif condition
            name_column = "tournament_name"
        else:
            logger.error(f"get_id_by_name: Invalid table name: {table}")
            return None

        query = f"SELECT {id_column} FROM {table} WHERE LOWER({name_column}) = LOWER(%s)" # Use name_column
        logger.info(f"get_id_by_name: Executing query: {query!r} with parameter: {name!r}")
        cursor.execute(query, (name,))
        result = cursor.fetchone()
        if result:
            #logger.info(f"get_id_by_name: Found {id_column}: {result[0]} for '{name}'")
            return result[0]
        else:
            #logger.info(f"get_id_by_name: No '{id_column}' found for '{name}' in table '{table}'")
            return None
    except mysql.connector.Error as e:
        logger.exception(f"get_id_by_name: Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

# Web routes for adding components and combinations

@app.route('/add_blade', methods=['GET', 'POST'])
def add_blade():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            blade_name = data['blade_name']
            canonical_name = data.get('canonical_name')
            blade_type = data['blade_type']
            spin_direction = data['spin_direction']

            cursor.execute("INSERT INTO Blades (blade_name, canonical_name, blade_type, spin_direction) VALUES (%s, %s, %s, %s)",
                           (blade_name, canonical_name, blade_type, spin_direction))
            blade_id = cursor.lastrowid

            # Handle stats, including weight
            if any(data.get(stat) for stat in ['attack', 'defense', 'stamina', 'weight']):
                attack = int(data.get('attack', 0)) if data.get('attack') else None
                defense = int(data.get('defense', 0)) if data.get('defense') else None
                stamina = int(data.get('stamina', 0)) if data.get('stamina') else None
                try:
                    weight_stat = float(data['weight']) if data.get('weight') else None
                except ValueError:
                    return "Invalid weight value. Please enter a number.", 400

                cursor.execute("""
                    INSERT INTO BladeStats (blade_id, attack, defense, stamina, weight)
                    VALUES (%s, %s, %s, %s, %s)
                """, (blade_id, attack, defense, stamina, weight_stat))

            conn.commit()
            conn.close()
            return "Blade added successfully!"
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
                conn.close()
            return f"Error adding blade: {e}", 400
    return render_template('add_blade.html')

@app.route('/add_ratchet', methods=['GET', 'POST'])
def add_ratchet():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            ratchet_name = data['ratchet_name']
            ratchet_protrusions = data['ratchet_protrusions']
            ratchet_base_height = data['ratchet_height']

            try:
                weight = float(data['ratchet_weight']) if data.get('ratchet_weight') else None
            except ValueError:
                return "Invalid weight value. Please enter a number.", 400

            cursor.execute("INSERT INTO Ratchets (ratchet_name, ratchet_protrusions, ratchet_height, ratchet_weight) VALUES (%s, %s, %s, %s)",
                           (ratchet_name, ratchet_protrusions, ratchet_base_height, weight))
            ratchet_id = cursor.lastrowid

            if any(data.get(stat) for stat in ['attack', 'defense', 'stamina', 'height']):
                attack = int(data.get('attack', 0)) if data.get('attack') else None
                defense = int(data.get('defense', 0)) if data.get('defense') else None
                stamina = int(data.get('stamina', 0)) if data.get('stamina') else None
                height = int(data.get('height', 0)) if data.get('height') else None #get height

                cursor.execute("""
                    INSERT INTO RatchetStats (ratchet_id, attack, defense, stamina, height)
                    VALUES (%s, %s, %s, %s, %s)
                """, (ratchet_id, attack, defense, stamina, height)) #insert height

            conn.commit()
            conn.close()
            return "Ratchet added successfully!"
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
                conn.close()
            return f"Error adding ratchet: {e}", 400
    return render_template('add_ratchet.html')

@app.route('/add_bit', methods=['GET', 'POST'])
def add_bit():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            bit_name = data['bit_name']
            full_bit_name = data['full_bit_name']
            bit_type = data['bit_type']

            try:
                weight = float(data['bit_weight']) if data.get('bit_weight') else None
            except ValueError:
                return "Invalid weight value. Please enter a number.", 400
            
            cursor.execute("INSERT INTO Bits (bit_name, full_bit_name, bit_weight, bit_type) VALUES (%s, %s, %s, %s)",
                           (bit_name, full_bit_name, weight, bit_type))
            bit_id = cursor.lastrowid

            # Insert stats only if they are provided
            if any(data.get(stat) for stat in ['attack', 'defense', 'stamina', 'dash', 'burst_resistance']):
                attack = int(data.get('attack', 0)) if data.get('attack') else None
                defense = int(data.get('defense', 0)) if data.get('defense') else None
                stamina = int(data.get('stamina', 0)) if data.get('stamina') else None
                dash = int(data.get('dash', 0)) if data.get('dash') else None
                burst_resistance = int(data.get('burst_resistance', 0)) if data.get('burst_resistance') else None

                cursor.execute("""
                    INSERT INTO BitStats (bit_id, attack, defense, stamina, dash, burst_resistance)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (bit_id, attack, defense, stamina, dash, burst_resistance))

            conn.commit()
            conn.close()
            return "Bit and stats added successfully!"
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
                conn.close()
            return f"Error adding bit: {e}", 400
    return render_template('add_bit.html')

@app.route('/add_combination', methods=['GET', 'POST'])
def add_combination():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT blade_name FROM Blades")
        blades = [{"name": row[0]} for row in cursor.fetchall()]
        cursor.execute("SELECT ratchet_name FROM Ratchets")
        ratchets = [{"name": row[0]} for row in cursor.fetchall()]
        cursor.execute("SELECT bit_name FROM Bits")
        bits = [{"name": row[0]} for row in cursor.fetchall()]

        if request.method == 'POST':
            data = request.form
            try:
                weight = float(data['combination_weight']) if data.get('combination_weight') else None
            except ValueError:
                return "Invalid weight value. Please enter a number.", 400
            
            try:
                cursor.execute("""
                    INSERT INTO BeybladeCombinations (blade_id, ratchet_id, bit_id, combination_name, combination_type, combination_weight)
                    VALUES ((SELECT blade_id FROM Blades WHERE blade_name = %s),
                            (SELECT ratchet_id FROM Ratchets WHERE ratchet_name = %s),
                            (SELECT bit_id FROM Bits WHERE bit_name = %s),
                            %s, %s, %s)
                """, (data['blade_name'], data['ratchet_name'], data['bit_name'], data['combination_name'], data['combination_type'], weight))
                conn.commit()
                return "Combination added successfully!"
            except mysql.connector.Error as e:
                conn.rollback()
                return f"Error adding combination: {e}", 400

    except mysql.connector.Error as e:
        return f"Error retrieving data: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('add_combination.html', blades=blades, ratchets=ratchets, bits=bits)

@app.route('/add_launcher', methods=['GET', 'POST'])
def add_launcher():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO LauncherTypes (launcher_name) VALUES (%s)", (data['launcher_name'],))
            conn.commit()
            conn.close()
            return "Launcher added successfully!"
        except mysql.connector.Error as e:
            conn.close()
            return f"Error adding launcher: {e}", 400
    return render_template('add_launcher.html')

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Players (player_name) VALUES (%s)", (data['player_name'],))
            conn.commit()
            conn.close()
            return "Player added successfully!"
        except mysql.connector.Error as e:
            conn.close()
            return f"Error adding player: {e}", 400
    return render_template('add_player.html')

@app.route('/add_tournament', methods=['GET', 'POST'])
def add_tournament():
    if request.method == 'POST':
        data = request.form

        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            # Attempt to parse date strings
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%dT%H:%M')
                logger.debug(f"Start Date (parsed): {start_date}")
            except ValueError as ve:
                logger.debug(f"Invalid start date format: {ve}")
                return "Invalid start date format. Please use YYYY-MM-DD HH:MM:SS", 400

            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%dT%H:%M')
                logger.debug(f"End Date (parsed): {end_date}")
            except ValueError as ve:
                logger.debug(f"Invalid end date format: {ve}")
                return "Invalid end date format. Please use YYYY-MM-DD HH:MM:SS", 400

            # Insert tournament data (assuming validation for other fields)
            cursor.execute("INSERT INTO Tournaments (tournament_name, start_date, end_date) VALUES (%s, %s, %s)",
                           (data['tournament_name'], start_date, end_date))
            conn.commit()
            conn.close()
            return "Tournament added successfully!"
        except mysql.connector.Error as e:
            logger.debug(f"Database Error: {e}")  # Print the full error for debugging
            return f"Error adding tournament: {e}", 500  # Return user-friendly error message
    return render_template('add_tournament.html')

@app.route('/add_match', methods=['GET', 'POST'], endpoint="add_match")
def add_match():
    conn = get_db_connection()  # Function to establish database connection
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    players = []
    combinations = []
    launchers = []
    tournaments = []
    stadiums = []
    message = None

    # Initialize all selected variables to None for the GET request
    player1_selected = None
    player2_selected = None
    p1_combo_selected = None
    p2_combo_selected = None
    p1_launcher_selected = None
    p2_launcher_selected = None
    winner_selected = None
    tournament_selected = None
    finish_selected = None
    stadium_selected = None

    try:
        # Fetch data for dropdowns (This is the same for both GET and POST)
        try:
            cursor.execute("SELECT player_name FROM Players")
            players = [{"player_name": player[0]} for player in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving players: {e}")

        try:
            cursor.execute("SELECT combination_name FROM BeybladeCombinations")
            combinations = [{"combination_name": combo[0]} for combo in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving combinations: {e}")

        try:
            cursor.execute("SELECT launcher_name FROM LauncherTypes")
            launchers = [{"launcher_name": launcher[0]} for launcher in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving launchers: {e}")

        try:
            cursor.execute("SELECT tournament_name, tournament_id FROM Tournaments")
            tournaments = [{"tournament_name": t[0], "tournament_id": t[1]} for t in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving tournaments: {e}")

        try:
            cursor.execute("SELECT stadium_name FROM Stadiums")
            stadiums = [{"stadium_name": stadium[0]} for stadium in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving stadiums: {e}")

        if request.method == 'POST':
            player1_name = request.form.get('player1_name')
            player2_name = request.form.get('player2_name')
            p1_combo_name = request.form.get('player1_combination_name')
            p2_combo_name = request.form.get('player2_combination_name')
            p1_launcher_name = request.form.get('player1_launcher_name')
            p2_launcher_name = request.form.get('player2_launcher_name')
            stadium_name = request.form.get('stadium_name')
            tournament_name = request.form.get('tournament_name')
            finish_type = request.form.get('finish_type')
            winner_name = request.form.get('winner_name')

            player1_id = get_id_by_name("Players", player1_name, "player_id")
            player2_id = get_id_by_name("Players", player2_name, "player_id")
            p1_combo_id = get_id_by_name("BeybladeCombinations", p1_combo_name, "combination_id")
            p2_combo_id = get_id_by_name("BeybladeCombinations", p2_combo_name, "combination_id")
            p1_launcher_id = get_id_by_name("LauncherTypes", p1_launcher_name, "launcher_id")
            p2_launcher_id = get_id_by_name("LauncherTypes", p2_launcher_name, "launcher_id")
            stadium_id = get_id_by_name("Stadiums", stadium_name, "stadium_id")
            tournament_id = None
            if tournament_name:
                tournament_id = get_id_by_name("Tournaments", tournament_name, "tournament_id")
            winner_id = None
            draw = False

            if finish_type == "Draw":
                draw = True
            elif winner_name:
                winner_id = get_id_by_name("Players", winner_name, "player_id")

            try:
                sql = """
                    INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, winner_id, finish_type, match_time, draw, stadium_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                val = (tournament_id, player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, winner_id, finish_type, datetime.now(), draw, stadium_id)

                cursor.execute(sql, val)
                conn.commit()

                # Publish updated stats to MQTT after successful commit
                publish_stats()

                message = "Match added successfully!"
                player1_selected = player1_name
                player2_selected = player2_name
                p1_combo_selected = p1_combo_name
                p2_combo_selected = p2_combo_name
                p1_launcher_selected = p1_launcher_name
                p2_launcher_selected = p2_launcher_name
                winner_selected = winner_name
                tournament_selected = tournament_name
                finish_selected = finish_type
                stadium_selected = stadium_name

            except mysql.connector.Error as e:
                conn.rollback()
                logger.error(f"Error adding match: {e}")
                message = f"Error adding match: {e}"
                return f"Error adding match: {e}", 500
            
        #GET Request
        else:
            message = request.args.get('message')
            player1_selected = request.args.get('player1_selected')
            player2_selected = request.args.get('player2_selected')
            p1_combo_selected = request.args.get('p1_combo_selected')
            p2_combo_selected = request.args.get('p2_combo_selected')
            p1_launcher_selected = request.args.get('p1_launcher_selected')
            p2_launcher_selected = request.args.get('p2_launcher_selected')
            winner_selected = request.args.get('winner_selected')
            tournament_selected = request.args.get('tournament_selected')
            finish_selected = request.args.get('finish_selected')
            stadium_selected = request.args.get('stadium_selected')

    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('add_match.html', players=players, combinations=combinations, launchers=launchers, tournaments=tournaments, stadiums=stadiums, message=message, player1_selected=player1_selected, player2_selected=player2_selected, p1_combo_selected=p1_combo_selected, p2_combo_selected=p2_combo_selected, p1_launcher_selected=p1_launcher_selected, p2_launcher_selected=p2_launcher_selected, winner_selected=winner_selected, tournament_selected=tournament_selected, finish_selected=finish_selected, stadium_selected=stadium_selected)

@app.route('/')  # Route for the landing page
def index():
    return render_template('index.html')

@app.route('/tournaments/stats', methods=['GET'])
def tournament_stats():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    tournaments = []
    all_tournaments = []
    tournament_stats = None
    overall_standings = []
    selected_tournament = request.args.get('tournament', None)

    try:
        # Get all tournaments for the dropdown
        try:
            cursor.execute("SELECT tournament_name, tournament_id FROM Tournaments")
            all_tournaments = [{"name": t[0], "id": t[1]} for t in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.error(f"Error retrieving tournaments for dropdown: {e}")

        # Construct WHERE clause for filtering
        where_clause = ""
        if selected_tournament:
            where_clause = f"WHERE t.tournament_id = {selected_tournament}"

        # Get Tournament and Match Data
        try:
            cursor.execute(f"""
                SELECT t.tournament_name, t.start_date, t.end_date, m.match_id,
                       p1.player_name AS player1_name, p2.player_name AS player2_name,
                       bc1.combination_name AS player1_combination, bc2.combination_name AS player2_combination,
                        lt1.launcher_name as player1_launcher, lt2.launcher_name as player2_launcher,
                       m.finish_type, COALESCE(w.player_name, 'Draw') AS winner_name, m.match_time
                FROM Tournaments t
                LEFT JOIN Matches m ON t.tournament_id = m.tournament_id
                LEFT JOIN Players p1 ON m.player1_id = p1.player_id
                LEFT JOIN Players p2 ON m.player2_id = p2.player_id
                LEFT JOIN BeybladeCombinations bc1 ON m.player1_combination_id = bc1.combination_id
                LEFT JOIN BeybladeCombinations bc2 ON m.player2_combination_id = bc2.combination_id
                LEFT JOIN LauncherTypes lt1 on m.player1_launcher_id = lt1.launcher_id
                LEFT JOIN LauncherTypes lt2 on m.player2_launcher_id = lt2.launcher_id
                LEFT JOIN Players w ON m.winner_id = w.player_id
                {where_clause}
                ORDER BY t.start_date DESC
            """)
            results = cursor.fetchall()
        except mysql.connector.Error as e:
            logger.error(f"Error retrieving tournament/match data: {e}")
            results = []

        # Process Tournament and Match Data
        tournaments_data = {}
        for row in results:
            tournament_name, start_date, end_date, match_id, player1_name, player2_name, player1_combination, player2_combination, player1_launcher, player2_launcher, finish_type, winner_name, match_time = row
            if tournament_name not in tournaments_data:
                tournaments_data[tournament_name] = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "matches": []
                }
            if match_id:
                tournaments_data[tournament_name]["matches"].append({
                    "match_id": match_id,
                    "player1": player1_name,
                    "player2": player2_name,
                    "player1_combination": player1_combination,
                    "player2_combination": player2_combination,
                    "player1_launcher":player1_launcher,
                    "player2_launcher":player2_launcher,
                    "finish_type": finish_type,
                    "winner": winner_name,
                    "match_time": match_time
                })

        tournaments = [] #reset the list to only include the selected tournament data
        for name, details in tournaments_data.items():
            tournaments.append({"name": name, "details": details})

        if selected_tournament and tournaments_data:
            tournament_name = list(tournaments_data.keys())[0]
            tournament_details = tournaments_data[tournament_name]
            tournament_stats = calculate_tournament_stats(tournament_details)
        else:
            tournament_stats = None

        #Overall Standings
        try:
            cursor.execute("""
                SELECT p.player_name, COUNT(m.winner_id) AS wins
                FROM Players p
                LEFT JOIN Matches m ON p.player_id = m.winner_id
                GROUP BY p.player_name
                ORDER BY wins DESC
            """)
            overall_standings = [{"player": row[0], "wins": row[1]} for row in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.error(f"Error retrieving overall standings: {e}")

    except mysql.connector.Error as e:
        logger.error(f"Outer database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('tournament_stats.html', tournaments=tournaments, all_tournaments=all_tournaments, selected_tournament=selected_tournament, tournament_stats=tournament_stats, overall_standings=overall_standings)

def calculate_tournament_stats(tournament):
    matches = tournament["matches"]
    player_wins = Counter()
    combination_wins = Counter()
    launchers_used = Counter()
    players = set()
    combinations = set()
    finish_types = Counter()
    num_draws = 0
    player_points = Counter()

    for match in matches:
        players.add(match["player1"])
        players.add(match["player2"])
        combinations.add(match["player1_combination"])
        combinations.add(match["player2_combination"])
        launchers_used[(match["player1"], match["player1_launcher"])] += 1
        launchers_used[(match["player2"], match["player2_launcher"])] += 1
        finish_types[match["finish_type"]] += 1

        if match["winner"] == "Draw":
            num_draws += 1
        elif match["winner"]: #check for a winner
            if match["finish_type"] == "Survivor":
                points = 1
            elif match["finish_type"] == "Burst":
                points = 2
            elif match["finish_type"] == "KO":
                points = 2
            elif match["finish_type"] == "Extreme":
                points = 3
            else:
                points = 0 # Default to 0 if finish type is unknown

            player_points[match["winner"]] += points
            player_wins[match["winner"]] += 1
            if match["winner"] == match["player1"]:
                combination_wins[match["player1_combination"]] += 1
            else:
                combination_wins[match["player2_combination"]] += 1

    winning_player_by_wins = player_wins.most_common(1)[0] if player_wins else None
    winning_combination_by_wins = combination_wins.most_common(1)[0] if combination_wins else None
    most_common_combination = combination_wins.most_common(1)[0] if combination_wins else None
    most_common_launcher = launchers_used.most_common(1)[0] if launchers_used else None
    most_common_finish_type = finish_types.most_common(1)[0] if finish_types else None
    num_wins = sum(player_wins.values())
    win_rate_by_finish = {}
    if num_wins > 0:
        wins_by_finish = Counter()
        for match in matches:
            if match["winner"] != "Draw" and match["winner"]:
                wins_by_finish[match["finish_type"]] += 1
        for finish, count in wins_by_finish.items():
            win_rate_by_finish[finish] = (count / num_wins) * 100

    # Sort Player Points (Largest to Smallest)
    sorted_player_points = sorted(player_points.items(), key=operator.itemgetter(1), reverse=True) if player_points else None

    # Sort Win Rate by Finish Type (Largest to Smallest)
    sorted_win_rate_by_finish = sorted(win_rate_by_finish.items(), key=operator.itemgetter(1), reverse=True) if win_rate_by_finish else None
    return {
        "num_players": len(players),
        "num_combinations": len(combinations),
        "player_wins": player_wins,
        "combination_wins": combination_wins,
        "winning_player_by_wins": winning_player_by_wins,
        "winning_combination_by_wins": winning_combination_by_wins,
        "most_common_combination": most_common_combination,
        "most_common_launcher": most_common_launcher,
        "most_common_finish_type": most_common_finish_type,
        "num_draws": num_draws,
        "win_rate_by_finish": sorted_win_rate_by_finish,
        "total_matches": len(matches),
        "player_points": sorted_player_points,
    }

@app.route('/players/stats', methods=['GET'])
def player_stats():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    all_players = []
    player_stats = None
    selected_player = request.args.get('player', None)

    try:
        # Get all players for the dropdown
        try:
            cursor.execute("SELECT player_name, player_id FROM Players")
            all_players = [{"name": p[0], "id": p[1]} for p in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.error(f"Error retrieving players for dropdown: {e}")

        if selected_player:
            try:
                cursor.execute(f"""
                    SELECT m.player1_id, m.player2_id,
                           m.player1_combination_id, m.player2_combination_id,
                           p.player_name as player1_name, p2.player_name as player2_name,
                           bc1.combination_name as player1_combination_name, bc2.combination_name as player2_combination_name,
                           lt1.launcher_name as player1_launcher, lt2.launcher_name as player2_launcher,
                           m.finish_type, COALESCE(w.player_name, 'Draw') AS winner_name, m.match_time,
                           t.tournament_name
                    FROM Matches m
                    LEFT JOIN Players p ON m.player1_id = p.player_id
                    LEFT JOIN Players p2 ON m.player2_id = p2.player_id
                    LEFT JOIN BeybladeCombinations bc1 ON m.player1_combination_id = bc1.combination_id
                    LEFT JOIN BeybladeCombinations bc2 ON m.player2_combination_id = bc2.combination_id
                    LEFT JOIN LauncherTypes lt1 ON m.player1_launcher_id = lt1.launcher_id
                    LEFT JOIN LauncherTypes lt2 ON m.player2_launcher_id = lt2.launcher_id
                    LEFT JOIN Players w ON m.winner_id = w.player_id
                    LEFT JOIN Tournaments t ON m.tournament_id = t.tournament_id
                    WHERE (m.player1_id = {selected_player} OR m.player2_id = {selected_player})
                    AND m.player1_id != m.player2_id
                    ORDER BY m.match_time DESC
                """)
                results = cursor.fetchall()
            except mysql.connector.Error as e:
                logger.error(f"Error retrieving player/match data: {e}")
                results = []

            player_data = {int(selected_player): {"matches": [], "name": None}}

            for row in results:
                p1_id, p2_id, p1_comb_id, p2_comb_id, p1_name, p2_name, p1_comb_name, p2_comb_name, p1_launcher, p2_launcher, finish, winner, time, tournament = row
                player_id = int(selected_player)

                if player_data[player_id]["name"] is None:
                    player_data[player_id]["name"] = p1_name if player_id == p1_id else p2_name

                opponent_name = p2_name if player_id == p1_id else p1_name
                player_combination = p1_comb_name if player_id == p1_id else p2_comb_name
                player_launcher = p1_launcher if player_id == p1_id else p2_launcher

                player_data[player_id]["matches"].append({
                    "opponent": opponent_name,
                    "finish_type": finish,
                    "winner": winner,
                    "match_time": time,
                    "tournament_name": tournament,
                    "player1": p1_name,
                    "player2": p2_name,
                    "player1_combination": p1_comb_name,
                    "player2_combination": p2_comb_name,
                    "player1_launcher": p1_launcher,
                    "player2_launcher": p2_launcher
                })

            player_details = player_data[int(selected_player)]
            player_stats = calculate_player_stats(player_details)
        

    except mysql.connector.Error as e:
        logger.error(f"Outer database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('player_stats.html', all_players=all_players, selected_player=selected_player, player_stats=player_stats)




def calculate_player_stats(player):
    matches = player["matches"]
    wins = 0
    losses = 0
    draws = 0
    win_by_finish = Counter()
    total_points = 0
    opponents = Counter()
    combinations_used = Counter()
    launchers_used = Counter()
    wins_against_each_opponent = Counter()
    matches_by_tournament = Counter()
    win_loss_streak = 0
    current_streak_type = None

    for match in matches:
        opponent = match["opponent"]
        opponents[opponent] += 1
        matches_by_tournament[match["tournament_name"]] += 1
        if player["name"] == match["player1"]:
            combinations_used[match["player1_combination"]] += 1
            launchers_used[match["player1_launcher"]] += 1
        elif player["name"] == match["player2"]:
            combinations_used[match["player2_combination"]] += 1
            launchers_used[match["player2_launcher"]] += 1

        if match["winner"] == player["name"]:
            result = "win"
        elif match["winner"] == "Draw":
            result = "draw"
        else:
            result = "loss"

        if result == "win":
            wins_against_each_opponent[opponent] += 1
            if match["finish_type"] == "Survivor":
                points = 1
            elif match["finish_type"] in ("Burst", "KO"):
                points = 2
            elif match["finish_type"] == "Extreme":
                points = 3
            else:
                points = 0
            wins += 1
            total_points += points
            win_by_finish[match["finish_type"]] += 1

            if current_streak_type == "win":
                win_loss_streak += 1
            else:
                current_streak_type = "win"
                win_loss_streak = 1

        elif result == "draw":
            draws += 1
            win_loss_streak = 0
            current_streak_type = None

        elif result == "loss":
            losses += 1
            if current_streak_type == "loss":
                win_loss_streak -= 1
            else:
                current_streak_type = "loss"
                win_loss_streak = -1

    total_matches_played = wins + losses + draws
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    most_frequent_opponent = opponents.most_common(1)[0] if opponents else None
    most_used_combination = combinations_used.most_common(1)[0] if combinations_used else None
    most_used_launcher = launchers_used.most_common(1)[0] if launchers_used else None
    favorite_win_type = win_by_finish.most_common(1)[0] if win_by_finish else None

    win_rate_against_each_opponent = {}
    for opp, wins_count in wins_against_each_opponent.items():
        total_matches_against_opp = opponents[opp]
        win_rate_against_each_opponent[opp] = (wins_count / total_matches_against_opp) * 100 if total_matches_against_opp > 0 else 0

    least_frequent_opponent = opponents.most_common()[-1] if opponents else None

    return {
        "name": player.get("name"),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "win_by_finish": win_by_finish,
        "total_points": total_points,
        "most_frequent_opponent": most_frequent_opponent,
        "total_matches_played": total_matches_played,
        "matches_by_tournament": matches_by_tournament,
        "most_used_combination": most_used_combination,
        "most_used_launcher": most_used_launcher,
        "win_rate_against_each_opponent": win_rate_against_each_opponent,
        "least_frequent_opponent": least_frequent_opponent,
        "favorite_win_type": favorite_win_type,
        "win_loss_streak": win_loss_streak
    }

@app.route('/combinations/stats', methods=['GET'])
def combinations_stats():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    all_combinations = []
    combination_stats = None
    selected_combination = request.args.get('combination', None)

    try:
        try:
            cursor.execute("SELECT combination_name, combination_id FROM BeybladeCombinations")
            all_combinations = [{"name": c[0], "id": c[1]} for c in cursor.fetchall()]
        except mysql.connector.Error as e:
            logger.error(f"Error retrieving combinations for dropdown: {e}")

        if selected_combination:
            try:
                cursor.execute(f"""
                    SELECT m.player1_id, m.player2_id,
                           p.player_name as player1_name, p2.player_name as player2_name,
                           bc1.combination_name as player1_combination, bc2.combination_name as player2_combination,
                           m.finish_type, COALESCE(w.player_name, 'Draw') AS winner_name, m.match_time,
                           t.tournament_name
                    FROM Matches m
                    LEFT JOIN Players p ON m.player1_id = p.player_id
                    LEFT JOIN Players p2 ON m.player2_id = p2.player_id
                    LEFT JOIN BeybladeCombinations bc1 ON m.player1_combination_id = bc1.combination_id
                    LEFT JOIN BeybladeCombinations bc2 ON m.player2_combination_id = bc2.combination_id
                    LEFT JOIN Players w ON m.winner_id = w.player_id
                    LEFT JOIN Tournaments t ON m.tournament_id = t.tournament_id
                    WHERE (m.player1_combination_id = {selected_combination} OR m.player2_combination_id = {selected_combination})
                    ORDER BY m.match_time DESC
                """)
                results = cursor.fetchall()
            except mysql.connector.Error as e:
                logger.error(f"Error retrieving match data for combination: {e}")
                results = []

            combination_data = {int(selected_combination): {"matches": [], "name": None}}

            for row in results:
                p1_id, p2_id, p1_name, p2_name, p1_comb, p2_comb, finish, winner, time, tournament = row
                comb_id = int(selected_combination)

                if combination_data[comb_id]["name"] is None:
                    combination_data[comb_id]["name"] = p1_comb if comb_id == p1_id else p2_comb

                combination_data[comb_id]["matches"].append({
                    "player1": p1_name,
                    "player2": p2_name,
                    "player1_combination": p1_comb,
                    "player2_combination": p2_comb,
                    "finish_type": finish,
                    "winner": winner,
                    "match_time": time,
                    "tournament_name": tournament
                })

            combination_details = combination_data[int(selected_combination)]
            combination_stats = calculate_combination_stats(combination_details)

    except mysql.connector.Error as e:
        logger.error(f"Outer database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('combinations_stats.html', all_combinations=all_combinations, selected_combination=selected_combination, combination_stats=combination_stats)

def calculate_combination_stats(combination):
    matches = combination["matches"]
    wins = 0
    losses = 0
    draws = 0
    opponent_stats = {}
    matches_by_tournament = Counter()
    most_frequent_loss_type = Counter()
    win_loss_streak = 0
    current_streak_type = None
    combination_name = combination["name"]

    for match in matches:
        player1_used_combination = match["player1_combination"] == combination_name
        player2_used_combination = match["player2_combination"] == combination_name

        if player1_used_combination and player2_used_combination: #handle combination vs combination matches
            if match["winner"] == "Draw":
                draws += 1
            elif match["winner"] == match["player1"]:
                wins += 1
            else:
                losses += 1
            matches_by_tournament[match["tournament_name"]] += 1
            continue


        if player1_used_combination:
            opponent = match["player2"]
            player_won = match["winner"] == match["player1"]
        elif player2_used_combination:
            opponent = match["player1"]
            player_won = match["winner"] == match["player2"]
        else:
            continue  # Skip if the combination wasn't used in this match

        matches_by_tournament[match["tournament_name"]] += 1

        if player_won:
            result = "win"
        elif match["winner"] == "Draw":
            result = "draw"
        else:
            result = "loss"

        opponent_stats.setdefault(opponent, {"wins": 0, "total": 0})["total"] += 1
        if result == "win":
            opponent_stats[opponent]["wins"] += 1
            wins += 1
            if current_streak_type == "win":
                win_loss_streak += 1
            else:
                current_streak_type = "win"
                win_loss_streak = 1
        elif result == "draw":
            draws += 1
            win_loss_streak = 0
            current_streak_type = None
        elif result == "loss":
            losses += 1
            most_frequent_loss_type[match["finish_type"]] += 1
            if current_streak_type == "loss":
                win_loss_streak -= 1
            else:
                current_streak_type = "loss"
                win_loss_streak = -1

    total_matches_played = wins + losses + draws
    win_rate = (wins / total_matches_played) * 100 if total_matches_played > 0 else 0
    most_frequent_loss = most_frequent_loss_type.most_common(1)[0] if most_frequent_loss_type else None

    win_rate_against_each_opponent = {}
    for opponent, stats in opponent_stats.items():
        win_rate_against_each_opponent[opponent] = (stats["wins"] / stats["total"]) * 100 if stats["total"] > 0 else 0

    return {
        "name": combination_name,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "total_matches_played": total_matches_played,
        "matches_by_tournament": matches_by_tournament,
        "win_rate_against_each_opponent": win_rate_against_each_opponent,
        "most_frequent_loss": most_frequent_loss,
        "win_loss_streak": win_loss_streak
    }

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    try:
        num_players = int(request.args.get('num_players', 5))
        if num_players < 1:
            num_players = 5

        tournament_id = request.args.get('tournament_id')
        columns_to_show = request.args.getlist('columns')

        where_clause = ""
        query_params = [num_players]

        if tournament_id:
            where_clause = "WHERE m.tournament_id = %s"
            query_params.insert(0, tournament_id)

        cursor.execute(f"""
            SELECT p.player_id, p.player_name,
                   COUNT(CASE WHEN m.winner_id = p.player_id THEN 1 END) AS wins,
                   COUNT(CASE WHEN (m.player1_id = p.player_id OR m.player2_id = p.player_id) AND m.winner_id != p.player_id AND m.draw = FALSE AND m.winner_id IS NOT NULL THEN 1 END) AS losses,
                   COUNT(CASE WHEN (m.player1_id = p.player_id OR m.player2_id = p.player_id) AND m.draw = TRUE THEN 1 END) AS draws,
                   SUM(CASE
                       WHEN m.winner_id = p.player_id AND m.finish_type = 'Survivor' THEN 1
                       WHEN m.winner_id = p.player_id AND (m.finish_type = 'Burst' OR m.finish_type = 'KO') THEN 2
                       WHEN m.winner_id = p.player_id AND m.finish_type = 'Extreme' THEN 3
                       ELSE 0
                   END) AS points
            FROM Players p
            LEFT JOIN Matches m ON p.player_id IN (m.player1_id, m.player2_id)
            {where_clause}
            GROUP BY p.player_id, p.player_name
            ORDER BY points DESC
            LIMIT %s
        """, tuple(query_params))

        player_results = cursor.fetchall()
        leaderboard_data = []
        rank = 1

        for player_id, player_name, wins, losses, draws, points in player_results:
            most_used_combination = "N/A"
            most_common_win_type = "N/A"
            most_common_loss_type = "N/A"

            combination_query_params = [player_id, player_id]
            win_type_query_params = [player_id]
            loss_type_query_params = [player_id, player_id, player_id]
            combination_where_clause = ""
            win_type_where_clause = ""
            loss_type_where_clause = ""

            if tournament_id:
                combination_where_clause = "AND m.tournament_id = %s"
                win_type_where_clause = "AND m.tournament_id = %s"
                loss_type_where_clause = "AND m.tournament_id = %s"
                combination_query_params.append(tournament_id)
                win_type_query_params.append(tournament_id)
                loss_type_query_params.append(tournament_id)

            cursor.execute(f"""
                SELECT bc.combination_name
                FROM Matches m
                JOIN BeybladeCombinations bc ON (
                    (m.player1_id = %s AND m.player1_combination_id = bc.combination_id) OR
                    (m.player2_id = %s AND m.player2_combination_id = bc.combination_id)
                )
                {combination_where_clause}
                GROUP BY bc.combination_name
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, tuple(combination_query_params))
            combination_result = cursor.fetchone()
            if combination_result:
                most_used_combination = combination_result[0]

            cursor.execute(f"""
                SELECT m.finish_type
                FROM Matches m
                WHERE m.winner_id = %s
                {win_type_where_clause}
                GROUP BY m.finish_type
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, tuple(win_type_query_params))
            win_type_result = cursor.fetchone()
            if win_type_result:
                most_common_win_type = win_type_result[0]

            cursor.execute(f"""
                SELECT m.finish_type
                FROM Matches m
                WHERE (m.player1_id = %s OR m.player2_id = %s) AND m.draw = FALSE AND m.winner_id != %s
                {loss_type_where_clause}
                GROUP BY m.finish_type
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, tuple(loss_type_query_params))
            loss_type_result = cursor.fetchone()
            if loss_type_result:
                most_common_loss_type = loss_type_result[0]

            leaderboard_data.append({
                "rank": rank,
                "name": player_name,
                "points": points,
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "most_used_combination": most_used_combination,
                "most_common_win_type": most_common_win_type,
                "most_common_loss_type": most_common_loss_type,
            })
            rank += 1

        try:
            cursor.execute("SELECT tournament_id, tournament_name FROM Tournaments")
            tournaments = cursor.fetchall()
            tournaments = [dict(zip([column[0] for column in cursor.description], row)) for row in tournaments]
        except mysql.connector.Error as e:
            logger.error(f"Error fetching tournaments: {e}")
            tournaments = []

        return render_template('leaderboard.html', leaderboard_data=leaderboard_data, num_players=num_players, columns_to_show=columns_to_show, tournament_id=tournament_id, tournaments=tournaments)

    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()


@app.route('/combination_leaderboard', methods=['GET'])
def combination_leaderboard():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor(dictionary=True)

    try:
        num_combinations = int(request.args.get('num_combinations', 5))
        if num_combinations < 1:
            num_combinations = 5

        tournament_id = request.args.get('tournament_id')
        columns_to_show = request.args.getlist('columns')
        if not columns_to_show:
            columns_to_show = ["rank", "name", "usage_count", "wins", "losses", "draws", "points", "win_rate", "most_used_by"]

        query = """
            SELECT bc.combination_id, bc.combination_name,
                   COUNT(m.match_id) AS usage_count,
                   SUM(CASE WHEN m.winner_id = m.player1_id AND m.player1_combination_id = bc.combination_id THEN 1
                            WHEN m.winner_id = m.player2_id AND m.player2_combination_id = bc.combination_id THEN 1
                            ELSE 0 END) AS wins,
                   SUM(CASE WHEN m.winner_id != m.player1_id AND m.player1_combination_id = bc.combination_id AND m.draw = FALSE AND m.winner_id IS NOT NULL THEN 1
                            WHEN m.winner_id != m.player2_id AND m.player2_combination_id = bc.combination_id AND m.draw = FALSE AND m.winner_id IS NOT NULL THEN 1
                            ELSE 0 END) AS losses,
                   SUM(CASE WHEN (m.player1_combination_id = bc.combination_id OR m.player2_combination_id = bc.combination_id) AND m.draw = TRUE THEN 1 ELSE 0 END) as draws,
                    SUM(CASE
                        WHEN (m.winner_id = m.player1_id AND m.player1_combination_id = bc.combination_id) AND m.finish_type = 'Survivor' THEN 1
                        WHEN (m.winner_id = m.player2_id AND m.player2_combination_id = bc.combination_id) AND m.finish_type = 'Survivor' THEN 1
                        WHEN (m.winner_id = m.player1_id AND m.player1_combination_id = bc.combination_id) AND (m.finish_type = 'Burst' OR m.finish_type = 'KO') THEN 2
                        WHEN (m.winner_id = m.player2_id AND m.player2_combination_id = bc.combination_id) AND (m.finish_type = 'Burst' OR m.finish_type = 'KO') THEN 2
                        WHEN (m.winner_id = m.player1_id AND m.player1_combination_id = bc.combination_id) AND m.finish_type = 'Extreme' THEN 3
                        WHEN (m.winner_id = m.player2_id AND m.player2_combination_id = bc.combination_id) AND m.finish_type = 'Extreme' THEN 3
                        ELSE 0
                    END) AS points,
                   (SELECT p.player_name
                    FROM Players p
                    INNER JOIN (
                        SELECT player1_id AS player_id, player1_combination_id AS combination_id FROM Matches %s
                        UNION ALL
                        SELECT player2_id, player2_combination_id FROM Matches %s
                    ) AS player_combinations ON p.player_id = player_combinations.player_id
                    WHERE player_combinations.combination_id = bc.combination_id
                    GROUP BY p.player_name ORDER BY COUNT(*) DESC LIMIT 1
                   ) AS most_used_by
            FROM BeybladeCombinations bc
            LEFT JOIN Matches m ON bc.combination_id IN (m.player1_combination_id, m.player2_combination_id)
            %s
            GROUP BY bc.combination_id, bc.combination_name
            ORDER BY points DESC, usage_count DESC
            LIMIT %s
        """

        query_params = []
        subquery_condition = ""
        main_query_condition = ""

        if tournament_id:
            subquery_condition = "WHERE tournament_id = %s"
            main_query_condition = "WHERE tournament_id = %s"
            query_params.extend([tournament_id, tournament_id, tournament_id])

        query_params.append(num_combinations)

        query = query % (subquery_condition, subquery_condition, main_query_condition, "%s")
        cursor.execute(query, tuple(query_params))

        combination_results = cursor.fetchall()

        leaderboard_data = []
        rank = 1
        for row in combination_results:
            row['rank'] = rank
            row['win_rate'] = (row.get('wins',0) / (row.get('wins',0) + row.get('losses',0)) * 100) if (row.get('wins',0) + row.get('losses',0)) > 0 else 0
            leaderboard_data.append(row)
            rank += 1

        try:
            cursor.execute("SELECT tournament_id, tournament_name FROM Tournaments")
            tournaments = cursor.fetchall()
            tournaments = [dict(row) for row in tournaments]
        except mysql.connector.Error as e:
            logger.error(f"Error fetching tournaments: {e}")
            tournaments = []

        return render_template('combination_leaderboard.html', 
                               leaderboard_data=leaderboard_data, 
                               num_combinations=num_combinations, 
                               tournament_id=tournament_id, 
                               tournaments=tournaments,
                               columns_to_show=columns_to_show)

    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

@app.route('/combinations/types', methods=['GET'])
def combinations_types_stats():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT bc1.combination_type, bc2.combination_type, COALESCE(w.player_name, 'Draw') AS winner_name, m.draw
                FROM Matches m
                LEFT JOIN BeybladeCombinations bc1 ON m.player1_combination_id = bc1.combination_id
                LEFT JOIN BeybladeCombinations bc2 ON m.player2_combination_id = bc2.combination_id
                LEFT JOIN Players w ON m.winner_id = w.player_id
            """)
            matches = cursor.fetchall()
            type_stats = calculate_combination_type_stats(matches)

    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('combinations_types.html', type_stats=type_stats)

def calculate_combination_type_stats(matches_data):
    type_usage = Counter()
    type_matchups = {}

    for p1_type, p2_type, winner_name, draw in matches_data:
        type_usage[p1_type] += 1
        type_usage[p2_type] += 1

        if draw or winner_name == 'Draw' or winner_name is None:
            continue

        matchup_key = tuple(sorted((p1_type, p2_type)))
        matchup = type_matchups.setdefault(matchup_key, {"p1_wins": 0, "p2_wins": 0, "total": 0})
        matchup["total"] += 1

        # Correctly determine the winner based on player names
        if winner_name in (p1_type, p2_type):  # If winner is a type
            if winner_name == p1_type:
                matchup["p1_wins"] += 1
            elif winner_name == p2_type:
                matchup["p2_wins"] += 1
        else:  # If winner is a player name
            for p1_type_check, p2_type_check, winner_check, draw_check in matches_data:
                if winner_check == winner_name and not draw_check:
                    if winner_check == p1_type_check: 
                        winner_type = p1_type_check
                    else:
                        winner_type = p2_type_check
                    if winner_type == p1_type:
                        matchup["p1_wins"] += 1
                    elif winner_type == p2_type:
                        matchup["p2_wins"] += 1
                    break 

    most_common_type = type_usage.most_common(1)[0] if type_usage else None

    for matchup_key, stats in type_matchups.items():
        total = stats["total"]
        type_matchups[matchup_key]["win_rates"] = {
            matchup_key[0]: round((stats["p1_wins"] / total) * 100, 1) if total > 0 else 0.0,
            matchup_key[1]: round((stats["p2_wins"] / total) * 100, 1) if total > 0 else 0.0
        }

    return {
        "most_common_type": most_common_type,
        "type_usage": type_usage,
        "type_matchups": type_matchups
    }

def publish_stats_to_mqtt(client):
    conn = get_db_connection()
    if conn is None:
        logger.error("Could not connect to database to publish MQTT stats.")
        return

    try:
        with conn.cursor() as cursor:
            # Total Matches
            cursor.execute("SELECT COUNT(*) FROM Matches WHERE draw = 0")
            total_matches = int(cursor.fetchone()[0])

            # Player Stats Query
            cursor.execute("""
                SELECT 
                    p.player_name,
                    SUM(CASE 
                        WHEN m.winner_id = p.player_id THEN
                            CASE m.finish_type
                                WHEN 'Survivor' THEN 1
                                WHEN 'Burst' THEN 2
                                WHEN 'KO' THEN 2
                                WHEN 'Extreme' THEN 3
                                ELSE 0
                            END
                        ELSE 0
                    END) AS total_points,
                  SUM(CASE WHEN m.winner_id = p.player_id THEN 1 ELSE 0 END) AS wins,
                  SUM(CASE WHEN m.winner_id != p.player_id AND m.winner_id IS NOT NULL THEN 1 ELSE 0 END) AS losses,
                  SUM(CASE WHEN m.draw = 1 THEN 1 ELSE 0 END) AS draws
                FROM Matches m
                INNER JOIN Players p ON m.player1_id = p.player_id OR m.player2_id = p.player_id
                GROUP BY p.player_name
                ORDER BY total_points DESC
                LIMIT 3;
            """)
            player_stats = cursor.fetchall()

            # Combination Stats Query
            cursor.execute("""
                SELECT 
                    bc.combination_name,
                    SUM(CASE 
                        WHEN m.player1_combination_id = bc.combination_id AND m.winner_id = m.player1_id THEN
                            CASE m.finish_type
                                WHEN 'Survivor' THEN 1
                                WHEN 'Burst' THEN 2
                                WHEN 'KO' THEN 2
                                WHEN 'Extreme' THEN 3
                                ELSE 0
                            END
                        WHEN m.player2_combination_id = bc.combination_id AND m.winner_id = m.player2_id THEN
                             CASE m.finish_type
                                WHEN 'Survivor' THEN 1
                                WHEN 'Burst' THEN 2
                                WHEN 'KO' THEN 2
                                WHEN 'Extreme' THEN 3
                                ELSE 0
                            END
                        ELSE 0  -- For losses and draws
                    END) AS total_points
                FROM Matches m
                INNER JOIN BeybladeCombinations bc ON m.player1_combination_id = bc.combination_id OR m.player2_combination_id = bc.combination_id
                GROUP BY bc.combination_name
                ORDER BY total_points DESC
                LIMIT 3;
            """)
            combination_stats = cursor.fetchall()

        # Publish to MQTT (Data and Discovery Messages)
        client.publish(MQTT_TOPIC_PREFIX + "total_matches", total_matches, retain=True)
        client.publish("homeassistant/sensor/beyblade_total_matches/config", json.dumps({
            "name": "Beyblade Total Matches",
            "state_topic": MQTT_TOPIC_PREFIX + "total_matches",
            "unit_of_measurement": "Matches",
            "state_class": "measurement",
            "icon": "mdi:counter"
        }), retain=True)

        for i, player in enumerate(player_stats):
            base_topic = MQTT_TOPIC_PREFIX + f"top_players/{i}/"
            player_name = player[0]
            player_points = player[1]
            player_wins = player[2]
            player_losses = player[3]
            player_draws = player[4]
            for player, points in player_points.items():
                # Ensure points is a Decimal object
                if isinstance(points, decimal.Decimal):
                    player_points[player] = str(points)  # Convert Decimal to string

            client.publish(base_topic + "name", player_name, retain=True)
            print(f"player_points data: {player_points}")  # Print the data for inspection
            player_points_json = json.dumps(player_points)
            client.publish(base_topic + "points", player_points_json, retain=True)
            client.publish(base_topic + "points", player_points, retain=True)
            client.publish(base_topic + "wins", player_wins, retain=True)
            client.publish(base_topic + "losses", player_losses, retain=True)
            client.publish(base_topic + "draws", player_draws, retain=True)

            discovery_config_name = {
                "name": f"Top Player {i+1} Name",
                "state_topic": base_topic + "name",
            }
            client.publish(f"homeassistant/sensor/top_player_{i+1}_name/config", json.dumps(discovery_config_name), retain=True)

            discovery_config_points = {
                "name": f"Top Player {i+1} Points",
                "state_topic": base_topic + "points",
                "unit_of_measurement": "Points",
                "state_class": "measurement",
                "icon": "mdi:trophy"
            }
            client.publish(f"homeassistant/sensor/top_player_{i+1}_points/config", json.dumps(discovery_config_points), retain=True)
            discovery_config_wins = {
                "name": f"Top Player {i+1} Wins",
                "state_topic": base_topic + "wins",
                "unit_of_measurement": "Wins",
                "state_class": "measurement",
                "icon": "mdi:trophy-variant"
            }
            client.publish(f"homeassistant/sensor/top_player_{i+1}_wins/config", json.dumps(discovery_config_wins), retain=True)
            discovery_config_losses = {
                "name": f"Top Player {i+1} Losses",
                "state_topic": base_topic + "losses",
                "unit_of_measurement": "Losses",
                "state_class": "measurement",
                "icon": "mdi:trophy-variant"
            }
            client.publish(f"homeassistant/sensor/top_player_{i+1}_losses/config", json.dumps(discovery_config_losses), retain=True)
            discovery_config_draws = {
                "name": f"Top Player {i+1} Draws",
                "state_topic": base_topic + "draws",
                "unit_of_measurement": "Draws",
                "state_class": "measurement",
                "icon": "mdi:trophy-variant"
            }
            client.publish(f"homeassistant/sensor/top_player_{i+1}_draws/config", json.dumps(discovery_config_draws), retain=True)


        for i, combination in enumerate(combination_stats):
            base_topic = MQTT_TOPIC_PREFIX + f"top_combinations/{i}/"
            combination_name = combination[0]
            combination_points = combination[1]

            client.publish(base_topic + "name", combination_name, retain=True)
            client.publish(base_topic + "points", combination_points, retain=True)

            discovery_config_points = {
                "name": f"Top Combination {i+1} Points",
                "state_topic": base_topic + "points",
                "unit_of_measurement": "Points",
                "state_class": "measurement",
                "icon": "mdi:trophy"
            }
            client.publish(f"homeassistant/sensor/top_combination_{i+1}_points/config", json.dumps(discovery_config_points), retain=True)
            discovery_config_name = {
                "name": f"Top Combination {i+1} Name",
                "state_topic": base_topic + "name",
            }
            client.publish(f"homeassistant/sensor/top_combination_{i+1}_name/config", json.dumps(discovery_config_name), retain=True)
        client.loop_start()  # Start the network loop
        client.publish("beyblade/stats", message_payload, qos=0)
        client.loop_stop()  # Stop the loop after publishing (optional)

    except mysql.connector.Error as e:
        logger.error(f"Database error in publish_stats_to_mqtt: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/api/beyblade_stats', methods=['GET'])
def beyblade_stats():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    try:
        with conn.cursor() as cursor:
            # Total Matches
            cursor.execute("SELECT COUNT(*) FROM Matches WHERE draw = 0")
            total_matches = int(cursor.fetchone()[0])

            # Player Stats Query
            cursor.execute("""
                SELECT 
                    p.player_name,
                    SUM(CASE 
                        WHEN m.winner_id = p.player_id THEN
                            CASE m.finish_type
                                WHEN 'Survivor' THEN 1
                                WHEN 'Burst' THEN 2
                                WHEN 'KO' THEN 2
                                WHEN 'Extreme' THEN 3
                                ELSE 0
                            END
                        ELSE 0
                    END) AS total_points,
                  SUM(CASE WHEN m.winner_id = p.player_id THEN 1 ELSE 0 END) AS wins,
                  SUM(CASE WHEN m.winner_id != p.player_id AND m.winner_id IS NOT NULL THEN 1 ELSE 0 END) AS losses,
                  SUM(CASE WHEN m.draw = 1 THEN 1 ELSE 0 END) AS draws
                FROM Matches m
                INNER JOIN Players p ON m.player1_id = p.player_id OR m.player2_id = p.player_id
                GROUP BY p.player_name
                ORDER BY total_points DESC
                LIMIT 3;
            """)
            player_stats = cursor.fetchall()

            # Combination Stats Query
            cursor.execute("""
                SELECT 
                    bc.combination_name,
                    SUM(CASE 
                        WHEN m.player1_combination_id = bc.combination_id AND m.winner_id = m.player1_id THEN
                            CASE m.finish_type
                                WHEN 'Survivor' THEN 1
                                WHEN 'Burst' THEN 2
                                WHEN 'KO' THEN 2
                                WHEN 'Extreme' THEN 3
                                ELSE 0
                            END
                        WHEN m.player2_combination_id = bc.combination_id AND m.winner_id = m.player2_id THEN
                             CASE m.finish_type
                                WHEN 'Survivor' THEN 1
                                WHEN 'Burst' THEN 2
                                WHEN 'KO' THEN 2
                                WHEN 'Extreme' THEN 3
                                ELSE 0
                            END
                        ELSE 0  -- For losses and draws
                    END) AS total_points
                FROM Matches m
                INNER JOIN BeybladeCombinations bc ON m.player1_combination_id = bc.combination_id OR m.player2_combination_id = bc.combination_id
                GROUP BY bc.combination_name
                ORDER BY total_points DESC
                LIMIT 3;
            """)
            combination_stats = cursor.fetchall()

        stats = {
            "total_matches": total_matches,
            "top_players": [
                {
                    "name": name,
                    "points": int(points),
                    "wins": int(wins),
                    "losses": int(losses),
                    "draws": int(draws)
                }
                for name, points, wins, losses, draws in player_stats
            ],
            "top_combinations": [
                {"name": name, "points": int(points)} for name, points in combination_stats
            ]
        }

        # Publish to MQTT
        publish_stats_to_mqtt(client)

        # Return JSON response
        return jsonify(stats)

    except mysql.connector.Error as e:
        logger.error(f"Database error in /api/beyblade_stats: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from datetime import datetime
from urllib.parse import unquote
import logging

# ... (other imports and app setup)

@app.route('/add_stadium', methods=['GET', 'POST'])
def add_stadium():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    message = None

    if request.method == 'POST':
        stadium_name = request.form['stadium_name']
        description = request.form.get('description', None) # Use .get to handle optional fields
        location = request.form.get('location', None)
        dimensions = request.form.get('dimensions', None)
        material = request.form.get('material', None)
        notes = request.form.get('notes', None)

        try:
            sql = """
                INSERT INTO Stadiums (stadium_name, description, location, dimensions, material, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            val = (stadium_name, description, location, dimensions, material, notes)
            cursor.execute(sql, val)
            conn.commit()
            message = "Stadium added successfully!"
        except mysql.connector.Error as e:
            conn.rollback()
            logger.error(f"Error adding stadium: {e}")
            message = f"Error adding stadium: {e}" # Display the error to the user for debugging
            return f"Error adding stadium: {e}", 500
        finally:
            conn.close()
        return redirect(url_for('add_stadium', message=message))
    elif request.method == 'GET':
        message = request.args.get('message')
        if message:
            return render_template('add_stadium.html', message=message)
        else:
            return render_template('add_stadium.html')

publish_stats_at_startup()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')