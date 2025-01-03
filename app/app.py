import os
from dotenv import load_dotenv
import mysql.connector
from flask import Flask, jsonify, request, render_template
from datetime import datetime

load_dotenv()

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
        print(f"Database connection error: {e}")
        return None

def get_id_by_name(table, name, id_column):
    conn = get_db_connection()
    if conn is None:
        print("get_id_by_name: Database connection failed")
        return None
    cursor = conn.cursor()
    try:
        name = name.strip()
        print(f"get_id_by_name: Looking for '{name}' in table '{table}'")
        # Make the comparison case-insensitive using LOWER()
        query = f"SELECT {id_column} FROM {table} WHERE LOWER(name) = LOWER(%s)"
        print(f"get_id_by_name: Executing query: {query} with name: {name}")
        cursor.execute(query, (name,))
        result = cursor.fetchone()
        if result:
            print(f"get_id_by_name: Found {id_column}: {result[0]} for '{name}'")
            return result[0]
        else:
            print(f"get_id_by_name: No '{id_column}' found for '{name}' in table '{table}'")
            return None
    except mysql.connector.Error as e:
        print(f"get_id_by_name: Database error: {e}")
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
            cursor.execute("INSERT INTO Blades (blade_name, canonical_name, blade_type, spin_direction, blade_weight) VALUES (%s, %s, %s, %s, %s)",
                           (data['blade_name'], data.get('canonical_name'), data['blade_type'], data['spin_direction'], data.get('blade_weight')))
            conn.commit()
            conn.close()
            return "Blade added successfully!"
        except mysql.connector.Error as e:
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
            cursor.execute("INSERT INTO Ratchets (ratchet_name, ratchet_protrusions, ratchet_height, ratchet_weight) VALUES (%s, %s, %s, %s)",
                           (data['ratchet_name'], data.get('ratchet_protrusions'), data.get('ratchet_height'), data.get('ratchet_weight')))
            conn.commit()
            conn.close()
            return "Ratchet added successfully!"
        except mysql.connector.Error as e:
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
            cursor.execute("INSERT INTO Bits (bit_name, bit_weight) VALUES (%s, %s)",
                           (data['bit_name'], data.get('bit_weight')))
            conn.commit()
            conn.close()
            return "Bit added successfully!"
        except mysql.connector.Error as e:
            conn.close()
            return f"Error adding bit: {e}", 400
    return render_template('add_bit.html')

@app.route('/add_combination', methods=['GET', 'POST'])
def add_combination():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    cursor.execute("SELECT blade_name, blade_weight FROM Blades")
    blades = cursor.fetchall()
    blade_list = []
    for blade in blades:
        blade_list.append({"blade_name": blade[0], "blade_weight": blade[1]})
    cursor.execute("SELECT ratchet_name, ratchet_weight FROM Ratchets")
    ratchets = cursor.fetchall()
    ratchet_list = []
    for ratchet in ratchets:
        ratchet_list.append({"ratchet_name": ratchet[0], "ratchet_weight": ratchet[1]})
    cursor.execute("SELECT bit_name, bit_weight FROM Bits")
    bits = cursor.fetchall()
    bit_list = []
    for bit in bits:
        bit_list.append({"bit_name": bit[0], "bit_weight": bit[1]})
    conn.close()

    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO BeybladeCombinations (blade_id, ratchet_id, bit_id, combination_name, combination_type, combination_weight)
                VALUES ((SELECT blade_id FROM Blades WHERE blade_name = %s),
                        (SELECT ratchet_id FROM Ratchets WHERE ratchet_name = %s),
                        (SELECT bit_id FROM Bits WHERE bit_name = %s),
                        %s, %s, %s)
            """, (data['blade_name'], data['ratchet_name'], data['bit_name'], data['combination_name'], data['combination_type'], data.get('combination_weight'))) #data.get to prevent errors if weight is empty
            conn.commit()
            conn.close()
            return "Combination added successfully!"
        except mysql.connector.Error as e:
            conn.close()
            return f"Error adding combination: {e}", 400
    return render_template('add_combination.html', blades=blade_list, ratchets=ratchet_list, bits=bit_list)

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
                print(f"Start Date (parsed): {start_date}")
            except ValueError as ve:
                print(f"Invalid start date format: {ve}")
                return "Invalid start date format. Please use YYYY-MM-DD HH:MM:SS", 400

            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%dT%H:%M')
                print(f"End Date (parsed): {end_date}")
            except ValueError as ve:
                print(f"Invalid end date format: {ve}")
                return "Invalid end date format. Please use YYYY-MM-DD HH:MM:SS", 400

            # Insert tournament data (assuming validation for other fields)
            cursor.execute("INSERT INTO Tournaments (tournament_name, start_date, end_date) VALUES (%s, %s, %s)",
                           (data['tournament_name'], start_date, end_date))
            conn.commit()
            conn.close()
            return "Tournament added successfully!"
        except mysql.connector.Error as e:
            print(f"Database Error: {e}")  # Print the full error for debugging
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
            print(f"Error retrieving players: {e}")

        try:
            cursor.execute("SELECT combination_name FROM BeybladeCombinations")
            combinations = cursor.fetchall()
            combination_list = [{"combination_name": combo[0]} for combo in combinations]
        except mysql.connector.Error as e:
            print(f"Error retrieving combinations: {e}")

        try:
            cursor.execute("SELECT launcher_name FROM LauncherTypes")
            launchers = cursor.fetchall()
            launcher_list = [{"launcher_name": launcher[0]} for launcher in launchers]
        except mysql.connector.Error as e:
            print(f"Error retrieving launchers: {e}")

        try:
            cursor.execute("SELECT tournament_name, tournament_id FROM Tournaments")
            tournaments = cursor.fetchall()
            tournament_list = [{"tournament_name": t[0], "tournament_id": t[1]} for t in tournaments]
        except mysql.connector.Error as e:
            print(f"Error retrieving tournaments: {e}")

        if request.method == 'POST':
            data = request.form
            print(f"Form Data: {data}")

            player1_id = get_id_by_name("Players", data['player1_name'], "player_id")
            if player1_id is None:
                return f"Invalid Player 1: {data['player1_name']}", 400

            player2_id = get_id_by_name("Players", data['player2_name'], "player_id")
            if player2_id is None:
                return f"Invalid Player 2: {data['player2_name']}", 400

            p1_combo_id = get_id_by_name("BeybladeCombinations", data['player1_combination_name'], "combination_id")
            if p1_combo_id is None:
                return f"Invalid Player 1 Combination: {data['player1_combination_name']}", 400

            p2_combo_id = get_id_by_name("BeybladeCombinations", data['player2_combination_name'], "combination_id")
            if p2_combo_id is None:
                return f"Invalid Player 2 Combination: {data['player2_combination_name']}", 400

            p1_launcher_id = get_id_by_name("LauncherTypes", data['player1_launcher_name'], "launcher_id")
            if p1_launcher_id is None:
                return f"Invalid Player 1 Launcher: {data['player1_launcher_name']}", 400

            p2_launcher_id = get_id_by_name("LauncherTypes", data['player2_launcher_name'], "launcher_id")
            if p2_launcher_id is None:
                return f"Invalid Player 2 Launcher: {data['player2_launcher_name']}", 400

            tournament_id = data.get('tournament_id')
            if tournament_id == "":
                tournament_id = None
            else:
                try:
                    tournament_id = int(tournament_id)
                except ValueError:
                    return "Invalid Tournament ID", 400

            winner_id = None
            if data['finish_type'] != "Draw":
                winner_id = get_id_by_name("Players", data['winner_name'], "player_id")
                if winner_id is None:
                    return f"Invalid Winner: {data['winner_name']}", 400

            try:
                if data['finish_type'] == "Draw":
                    sql = """
                        INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, finish_type, match_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    val = (tournament_id, player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, data['finish_type'], datetime.now())
                else:
                    sql = """
                        INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, winner_id, finish_type, match_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    val = (tournament_id, player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, winner_id, data['finish_type'], datetime.now())

                print(f"Executing SQL: {sql} with values: {val}")
                cursor.execute(sql, val)
                conn.commit()
                return "Match added successfully!"
            except mysql.connector.Error as e:
                print(f"Database Error during insert: {e}")
                return f"Error adding match: {e}", 500

    except mysql.connector.Error as e:
        print(f"Database error: {e}", 500)
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
