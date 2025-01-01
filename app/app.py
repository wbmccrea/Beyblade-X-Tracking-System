from flask import Flask, jsonify, request
import mysql.connector
import datetime
import os

app = Flask(__name__)

# Database configuration (using environment variables)
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

def get_db_connection():
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return mydb
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# Helper function to get ID by name
def get_id_by_name(table, name):
    conn = get_db_connection()
    if conn is None:
        return None
    cursor = conn.cursor()
    query = f"SELECT {table[:-1]}_id FROM {table} WHERE {table[:-1]}_name = %s"
    cursor.execute(query, (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Example API endpoint for calculating player vs. player win rate
@app.route('/api/winrate/<player1_name>/<player2_name>', methods=['GET'])
def get_win_rate(player1_name, player2_name):
    player1_id = get_id_by_name("Players", player1_name)
    player2_id = get_id_by_name("Players", player2_name)

    if not player1_id or not player2_id:
        return jsonify({"error": "Players not found"}), 404
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to Database"}), 500
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            SUM(CASE WHEN winner_id = %s THEN 1 ELSE 0 END) AS player1_wins,
            COUNT(*) AS total_matches
        FROM Matches
        WHERE (player1_id = %s AND player2_id = %s) OR (player1_id = %s AND player2_id = %s)
    """, (player1_id, player1_id, player2_id, player2_id, player1_id))

    result = cursor.fetchone()
    conn.close()

    if result[1] == 0:
        win_rate = 0
    else:
        win_rate = (result[0] / result[1]) * 100

    return jsonify({"player1": player1_name, "player2": player2_name, "win_rate": win_rate})

# Example API endpoint to add a match
@app.route('/api/matches', methods=['POST'])
def add_match():
    data = request.get_json()

    # Get IDs based on names or combination names
    player1_id = get_id_by_name("Players", data.get('player1_name'))
    player2_id = get_id_by_name("Players", data.get('player2_name'))
    p1_combo_id = get_id_by_name("BeybladeCombinations", data.get('player1_combination_name'))
    p2_combo_id = get_id_by_name("BeybladeCombinations", data.get('player2_combination_name'))
    p1_launcher_id = get_id_by_name("LauncherTypes", data.get('player1_launcher_name'))
    p2_launcher_id = get_id_by_name("LauncherTypes", data.get('player2_launcher_name'))

    if not player1_id or not player2_id or not p1_combo_id or not p2_combo_id or not p1_launcher_id or not p2_launcher_id:
        return jsonify({'error': 'Missing or invalid player, combination, or launcher name'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to Database"}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Matches (tournament_id, player1_id, player2_id, player1_combination_id, player2_combination_id, player1_launcher_id, player2_launcher_id, winner_id, finish_type, match_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (data.get('tournament_id'), player1_id, player2_id, p1_combo_id, p2_combo_id, p1_launcher_id, p2_launcher_id, data.get('winner_id'), data.get('finish_type'), datetime.datetime.now()))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Match added successfully'}), 201
    except mysql.connector.Error as e:
        conn.close()
        return jsonify({'error': str(e)}), 400

# Example API endpoint to add a player
@app.route('/api/players', methods=['POST'])
def add_player():
    data = request.get_json()
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to Database"}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Players (player_name) VALUES (%s)", (data['player_name'],))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Player added successfully'}), 201
    except mysql.connector.Error as e:
        conn.close()
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
