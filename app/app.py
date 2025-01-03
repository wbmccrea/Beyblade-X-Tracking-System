import os
from dotenv import load_dotenv
import mysql.connector
from flask import Flask, jsonify, request, render_template
from datetime import datetime
from urllib.parse import unquote
import logging

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
        cursor.execute("SELECT blade_name FROM Blades")  # Only select names
        blades = cursor.fetchall()
        cursor.execute("SELECT ratchet_name FROM Ratchets")  # Only select names
        ratchets = cursor.fetchall()
        cursor.execute("SELECT bit_name FROM Bits")  # Only select names
        bits = cursor.fetchall()

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
    player_list = []
    combination_list = []
    launcher_list = []
    tournament_list = []

    try:
        try:
            cursor.execute("SELECT player_name FROM Players")
            players = cursor.fetchall()
            player_list = [{"player_name": player[0]} for player in players]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving players: {e}")

        try:
            cursor.execute("SELECT combination_name FROM BeybladeCombinations")
            combinations = cursor.fetchall()
            combination_list = [{"combination_name": combo[0]} for combo in combinations]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving combinations: {e}")

        try:
            cursor.execute("SELECT launcher_name FROM LauncherTypes")
            launchers = cursor.fetchall()
            launcher_list = [{"launcher_name": launcher[0]} for launcher in launchers]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving launchers: {e}")

        try:
            cursor.execute("SELECT tournament_name, tournament_id FROM Tournaments")
            tournaments = cursor.fetchall()
            tournament_list = [{"tournament_name": t[0], "tournament_id": t[1]} for t in tournaments]
        except mysql.connector.Error as e:
            logger.debug(f"Error retrieving tournaments: {e}")

        if request.method == 'POST':
            data = request.form
            logger.debug(f"Raw Form Data: {data}")

            decoded_data = {}
            for key, value in data.items():
                decoded_data[key] = unquote(value)
            logger.debug(f"Decoded Form Data: {decoded_data}")

            player1_id = get_id_by_name("Players", decoded_data['player1_name'], "player_id")
            if player1_id is None:
                return f"Invalid Player 1: {decoded_data['player1_name']}", 400

            player2_id = get_id_by_name("Players", decoded_data['player2_name'], "player_id")
            if player2_id is None:
                return f"Invalid Player 2: {decoded_data['player2_name']}", 400

            p1_combo_id = get_id_by_name("BeybladeCombinations", decoded_data['player1_combination_name'], "combination_id")
            if p1_combo_id is None:
                return f"Invalid Player 1 Combination: {decoded_data['player1_combination_name']}", 400

            p2_combo_id = get_id_by_name("BeybladeCombinations", decoded_data['player2_combination_name'], "combination_id")
            if p2_combo_id is None:
                return f"Invalid Player 2 Combination: {decoded_data['player2_combination_name']}", 400

            p1_launcher_id = get_id_by_name("LauncherTypes", decoded_data['player1_launcher_name'], "launcher_id")
            if p1_launcher_id is None:
                return f"Invalid Player 1 Launcher: {decoded_data['player1_launcher_name']}", 400

            p2_launcher_id = get_id_by_name("LauncherTypes", decoded_data['player2_launcher_name'], "launcher_id")
            if p2_launcher_id is None:
                return f"Invalid Player 2 Launcher: {decoded_data['player2_launcher_name']}", 400

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
                if winner_id is None:
                    return f"Invalid Winner: {decoded_data['winner_name']}", 400

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

                logger.debug(f"Executing SQL: {sql} with values: {val}")
                cursor.execute(sql, val)
                conn.commit()
                return "Match added successfully!"
            except mysql.connector.Error as e:
                logger.debug(f"Database Error during insert: {e}")
                return f"Error adding match: {e}", 500

    except mysql.connector.Error as e:
        logger.debug(f"Database error: {e}", 500)
        return f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()

    return render_template('add_match.html', players=player_list, combinations=combination_list, launchers=launcher_list, tournaments=tournament_list)

@app.route('/')  # Route for the landing page
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
