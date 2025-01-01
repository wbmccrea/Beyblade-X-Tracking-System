from flask import Flask, jsonify, request, render_template, send_from_directory
import mysql.connector
import datetime
import os

app = Flask(__name__)

# Database configuration (replace with your credentials)
db_config = {
    "user": "your_username",
    "password": "your_password",
    "host": "your_host",
    "database": "your_database"
}


def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print("Error connecting to database:", err)
        return None


# Helper function to get ID by name
def get_id_by_name(table, name):
    conn = get_db_connection()
    if conn is None:
        return None
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM {table} WHERE name = %s", (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None



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
        # ... (rest of the POST handling code - no changes)
        pass #this is here to prevent an indentation error. Remove this line
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
            start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d %H:%M:%S')
            end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d %H:%M:%S')

            cursor.execute("INSERT INTO Tournaments (tournament_name, start_date, end_date) VALUES (%s, %s, %s)",
                           (data['tournament_name'], start_date, end_date))
            conn.commit()
            conn.close()
            return "Tournament added successfully!"
        except mysql.connector.Error as e:
            conn.close()
            return f"Error adding tournament: {e}", 400
        except ValueError:
            conn.close()
            return "Invalid date format. Please use YYYY-MM-DD HH:MM:SS", 400
    return render_template('add_tournament.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

@app.route('/add_match', methods=['GET', 'POST'])
def add_match():
    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()

    cursor.execute("SELECT player_name FROM Players")
    players = cursor.fetchall()
    player_list = []
    for player in players:
        player_list.append({"player_name": player[0]})

    cursor.execute("SELECT combination_name FROM BeybladeCombinations")
    combinations = cursor.fetchall()
    combination_list = []
    for combination in combinations:
        combination_list.append({"combination_name": combination[0]})

    cursor.execute("SELECT launcher_name FROM LauncherTypes")
    launchers = cursor.fetchall()
    launcher_list = []
    for launcher in launchers:
        launcher_list.append({"launcher_name": launcher[0]})

    cursor.execute("SELECT tournament_name, tournament_id FROM Tournaments")
    tournaments = cursor.fetchall()
    tournament_list = []
    for tournament in tournaments:
        tournament_list.append({"tournament_name": tournament[0], "tournament_id": tournament[1]})
    conn.close()

    if request.method == 'POST':
        data = request.form

        player1_id = get_id_by_name("Players", data['player1_name'])
        player2_id = get_id_by_name("Players", data['player2_name'])
        p1_combo_id = get_id_by_name("BeybladeCombinations", data['player1_combination_name'])
        p2_combo_id = get_id_by_name("BeybladeCombinations", data['player2_combination_name'])
        p1_launcher_id = get_id_by_name("LauncherTypes", data['player1_launcher_name'])
        p2_launcher_id = get_id_by_name("LauncherTypes", data['player2_launcher_name'])
        winner_id = get_id_by_name("Players", data['winner_name'])
        tournament_id = data.get('tournament_id') # Get the tournament id, could be None

        if not player1_id or not player2_id or not p1_combo_id or not p2_combo_id or not p1_launcher_id or not p2_launcher_id or not winner_id:
            return "Invalid player, combination, launcher or winner name", 400

        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, winner_id, finish_type, match_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (tournament_id, player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, winner_id, data['finish_type'], datetime.datetime.now()))
            conn.commit()
            conn.close()
            return "Match added successfully!"
        except mysql.connector.Error as e:
            conn.close()
            return f"Error adding match: {e}", 400
    return render_template('add_match.html', players=player_list, combinations=combination_list, launchers=launcher_list, tournaments=tournament_list)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

@app.route('/')  # Route for the landing page
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
