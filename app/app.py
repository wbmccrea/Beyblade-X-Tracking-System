import os
from dotenv import load_dotenv
import mysql.connector
from flask import Flask, jsonify, request, render_template
from datetime import datetime
from urllib.parse import unquote
import logging
from collections import Counter
import operator

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logger = logging.getLogger(__name__) #get a logger object


app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

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

def get_id_by_name(table, name, id_column):
    conn = get_db_connection()
    if conn is None:
        logger.error("get_id_by_name: Database connection failed")
        return None
    cursor = conn.cursor()
    try:
        name = name.strip()
        logger.info(f"get_id_by_name: Looking for '{name}' in table '{table}'")

        if table == "Players":
            name_column = "player_name"
        elif table == "BeybladeCombinations":
            name_column = "combination_name"
        elif table == "LauncherTypes":
            name_column = "launcher_name"
        else:
            logger.error(f"get_id_by_name: Invalid table name: {table}")
            return None

        query = f"SELECT {id_column} FROM {table} WHERE LOWER({name_column}) = LOWER(%s)" # Use name_column
        logger.info(f"get_id_by_name: Executing query: {query!r} with parameter: {name!r}")
        cursor.execute(query, (name,))
        result = cursor.fetchone()
        if result:
            logger.info(f"get_id_by_name: Found {id_column}: {result[0]} for '{name}'")
            return result[0]
        else:
            logger.info(f"get_id_by_name: No '{id_column}' found for '{name}' in table '{table}'")
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

@app.route('/add_match', methods=['GET', 'POST'])
def add_match():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    players = []
    combinations = []
    launchers = []
    tournaments = []
    message = None
    player1_selected = None
    player2_selected = None
    p1_combo_selected = None
    p2_combo_selected = None
    p1_launcher_selected = None
    p2_launcher_selected = None
    winner_selected = None
    tournament_selected = None
    finish_selected = None

    try:
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


        if request.method == 'POST':
            data = request.form
            decoded_data = {}
            for key, value in data.items():
                decoded_data[key] = unquote(value)

            player1_id = get_id_by_name("Players", decoded_data['player1_name'], "player_id")
            player2_id = get_id_by_name("Players", decoded_data['player2_name'], "player_id")
            p1_combo_id = get_id_by_name("BeybladeCombinations", decoded_data['player1_combination_name'], "combination_id")
            p2_combo_id = get_id_by_name("BeybladeCombinations", decoded_data['player2_combination_name'], "combination_id")
            p1_launcher_id = get_id_by_name("LauncherTypes", decoded_data['player1_launcher_name'], "launcher_id")
            p2_launcher_id = get_id_by_name("LauncherTypes", decoded_data['player2_launcher_name'], "launcher_id")

            tournament_id = decoded_data.get('tournament_id')
            if tournament_id == "":
                tournament_id = None
            else:
                try:
                    tournament_id = int(tournament_id)
                except ValueError:
                    return "Invalid Tournament ID", 400

            winner_id = None
            if decoded_data['finish_type'] != "Draw":
                winner_id = get_id_by_name("Players", decoded_data['winner_name'], "player_id")

            try:
                if decoded_data['finish_type'] == "Draw":
                    sql = """
                        INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, finish_type, match_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    val = (tournament_id, player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, decoded_data['finish_type'], datetime.now())
                else:
                    sql = """
                        INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, winner_id, finish_type, match_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    val = (tournament_id, player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, winner_id, decoded_data['finish_type'], datetime.now())

                cursor.execute(sql, val)
                conn.commit()

                message = "Match added successfully!"
                player1_selected = decoded_data.get('player1_name')
                player2_selected = decoded_data.get('player2_name')
                p1_combo_selected = decoded_data.get('player1_combination_name')
                p2_combo_selected = decoded_data.get('player2_combination_name')
                p1_launcher_selected = decoded_data.get('player1_launcher_name')
                p2_launcher_selected = decoded_data.get('player2_launcher_name')
                winner_selected = decoded_data.get('winner_name')
                tournament_selected = int(decoded_data.get('tournament_id')) if decoded_data.get('tournament_id') else None
                finish_selected = decoded_data.get('finish_type')

            except mysql.connector.Error as e:
                conn.rollback()
                return f"Error adding match: {e}", 500

    except mysql.connector.Error as e:
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('add_match.html', players=players, combinations=combinations, launchers=launchers, tournaments=tournaments, message=message, player1_selected=player1_selected, player2_selected=player2_selected, p1_combo_selected=p1_combo_selected, p2_combo_selected=p2_combo_selected, p1_launcher_selected=p1_launcher_selected, p2_launcher_selected=p2_launcher_selected, winner_selected=winner_selected, tournament_selected=tournament_selected, finish_selected=finish_selected)

@app.route('/')  # Route for the landing page
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

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

    players = []
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

        # Construct WHERE clause for filtering
        where_clause = ""
        if selected_player:
            where_clause = f"WHERE (m.player1_id = {selected_player} OR m.player2_id = {selected_player})"

        # Get Player and Match Data (Corrected Query)
        try:
            cursor.execute(f"""
                SELECT p.player_name, m.match_id,
                       p1.player_name AS opponent_name,
                       m.finish_type, COALESCE(w.player_name, 'Draw') AS winner_name, m.match_time,
                       t.tournament_name
                FROM Players p
                LEFT JOIN Matches m ON (p.player_id = m.player1_id OR p.player_id = m.player2_id)
                LEFT JOIN Players p1 ON (CASE WHEN p.player_id = m.player1_id THEN m.player2_id ELSE m.player1_id END) = p1.player_id
                LEFT JOIN Players w ON m.winner_id = w.player_id
                LEFT JOIN Tournaments t ON m.tournament_id = t.tournament_id
                {where_clause}
                AND m.player1_id != m.player2_id  -- Exclude self-matches
                ORDER BY m.match_time DESC
            """)
            results = cursor.fetchall()
        except mysql.connector.Error as e:
            logger.error(f"Error retrieving player/match data: {e}")
            results = []

        player_data = {}
        for row in results:
            player_name, match_id, opponent_name, finish_type, winner_name, match_time, tournament_name = row
            if player_name not in player_data:
                player_data[player_name] = {
                    "matches": []
                }
            if match_id:
                player_data[player_name]["matches"].append({
                    "match_id": match_id,
                    "opponent": opponent_name,
                    "finish_type": finish_type,
                    "winner": winner_name,
                    "match_time": match_time,
                    "tournament_name": tournament_name
                })

        players = []
        for name, details in player_data.items():
            players.append({"name": name, "details": details})

        if selected_player and player_data:
            player_name = list(player_data.keys())[0]
            player_details = player_data[player_name]
            player_details["name"] = player_name
            player_stats = calculate_player_stats(player_details)
            player_stats["name"] = player_name  # Add the name here!
        else:
            player_stats = None

    except mysql.connector.Error as e:
        logger.error(f"Outer database error: {e}")
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('player_stats.html', players=players, all_players=all_players, selected_player=selected_player, player_stats=player_stats)


def calculate_player_stats(player):
    matches = player["matches"]
    wins = 0
    losses = 0
    draws = 0
    win_by_finish = Counter()
    total_points = 0
    opponents = Counter()

    for match in matches:
        opponent = match["opponent"]
        opponents[opponent] += 1

        if match["winner"] == player["name"]:
            result = "win"
        elif match["winner"] == "Draw":
            result = "draw"
        else:
            result = "loss"

        if result == "win":
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
        elif result == "draw":
            draws += 1
        elif result == "loss":
            losses += 1

    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    most_frequent_opponent = opponents.most_common(1)[0] if opponents else None

    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "win_by_finish": win_by_finish,
        "total_points": total_points,
        "most_frequent_opponent": most_frequent_opponent,
        "name": player.get("name") #ensure the name is passed back
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)