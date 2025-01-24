-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS beyblade_db;

-- Use the database
USE beyblade_db;

-- Players table (No changes)
CREATE TABLE IF NOT EXISTS Players (
    player_id INT AUTO_INCREMENT PRIMARY KEY,
    player_name VARCHAR(255) UNIQUE
);

-- Blades table (No changes)
CREATE TABLE IF NOT EXISTS Blades (
    blade_id INT AUTO_INCREMENT PRIMARY KEY,
    blade_name VARCHAR(255) UNIQUE,
    canonical_name VARCHAR(255),
    blade_type ENUM('Attack', 'Defense', 'Stamina', 'Balance', 'None'),
    spin_direction ENUM('Right-Spin', 'Left-Spin', 'Dual-Spin'),
    blade_weight DECIMAL(4, 1) DEFAULT NULL
);

-- Ratchets table (No changes)
CREATE TABLE IF NOT EXISTS Ratchets (
    ratchet_id INT AUTO_INCREMENT PRIMARY KEY,
    ratchet_name VARCHAR(255) UNIQUE,
    ratchet_protrusions INT,
    ratchet_height INT,
    ratchet_weight DECIMAL(4, 1) DEFAULT NULL
);

-- Bits table (No changes)
CREATE TABLE IF NOT EXISTS Bits (
    bit_id INT AUTO_INCREMENT PRIMARY KEY,
    bit_name VARCHAR(255) UNIQUE,
    full_bit_name VARCHAR(255),
    bit_weight DECIMAL(4, 1) DEFAULT NULL,
    bit_type ENUM('Attack', 'Defense', 'Stamina', 'Balance', 'Unknown') DEFAULT 'Unknown'
);

-- BitStats table (No changes)
CREATE TABLE IF NOT EXISTS BitStats (
    bit_id INT PRIMARY KEY,
    attack INT DEFAULT 0,
    defense INT DEFAULT 0,
    stamina INT DEFAULT 0,
    dash INT DEFAULT 0,
    burst_resistance INT DEFAULT 0,
    FOREIGN KEY (bit_id) REFERENCES Bits(bit_id)
);

-- BladeStats table (No changes)
CREATE TABLE IF NOT EXISTS BladeStats (
    blade_id INT PRIMARY KEY,
    attack INT DEFAULT 0,
    defense INT DEFAULT 0,
    stamina INT DEFAULT 0,
    weight DECIMAL(4, 1) DEFAULT NULL,
    FOREIGN KEY (blade_id) REFERENCES Blades(blade_id)
);

-- RatchetStats table (No changes)
CREATE TABLE IF NOT EXISTS RatchetStats (
    ratchet_id INT PRIMARY KEY,
    attack INT DEFAULT 0,
    defense INT DEFAULT 0,
    stamina INT DEFAULT 0,
    height int DEFAULT 0,
    FOREIGN KEY (ratchet_id) REFERENCES Ratchets(ratchet_id)
);

-- BladeAliases table (No changes)
CREATE TABLE IF NOT EXISTS BladeAliases (
    alias_id INT AUTO_INCREMENT PRIMARY KEY,
    blade_id INT,
    alias_name VARCHAR(255) UNIQUE,
    FOREIGN KEY (blade_id) REFERENCES Blades(blade_id)
);

-- BeybladeCombinations table (No changes)
CREATE TABLE IF NOT EXISTS BeybladeCombinations (
    combination_id INT AUTO_INCREMENT PRIMARY KEY,
    blade_id INT,
    ratchet_id INT,
    bit_id INT,
    combination_name VARCHAR(255) UNIQUE,
    combination_type ENUM('Attack', 'Defense', 'Stamina', 'Balance', 'Unknown'),
    combination_weight DECIMAL(5, 2) DEFAULT NULL,
    FOREIGN KEY (blade_id) REFERENCES Blades(blade_id),
    FOREIGN KEY (ratchet_id) REFERENCES Ratchets(ratchet_id),
    FOREIGN KEY (bit_id) REFERENCES Bits(bit_id)
);

-- Launchers table (renamed from LauncherTypes, added launcher_class_id)
CREATE TABLE IF NOT EXISTS Launchers (
    launcher_id INT AUTO_INCREMENT PRIMARY KEY,
    launcher_name VARCHAR(255) UNIQUE,
    launcher_class_id INT,
    FOREIGN KEY (launcher_class_id) REFERENCES LauncherClasses(id)
);

-- LauncherClasses table
CREATE TABLE IF NOT EXISTS LauncherClasses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    description VARCHAR(255)
);

-- LauncherClass_spin_compatibility table
CREATE TABLE IF NOT EXISTS LauncherClass_spin_compatibility (
    launcher_class_id INT,
    spin_direction ENUM('Right-Spin', 'Left-Spin', 'Dual-Spin'),
    FOREIGN KEY (launcher_class_id) REFERENCES LauncherClasses(id),
    PRIMARY KEY (launcher_class_id, spin_direction)
);

-- Tournaments table (added tournament_type)
CREATE TABLE IF NOT EXISTS Tournaments (
    tournament_id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_name VARCHAR(255),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    tournament_type ENUM('Standard', 'PlayerLadder', 'CombinationLadder') DEFAULT 'Standard'
);

-- Matches table (added start_time, renamed match_time to end_time)
CREATE TABLE IF NOT EXISTS Matches (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT,
    player1_id INT,
    player2_id INT,
    player1_combination_id INT,
    player2_combination_id INT,
    player1_launcher_id INT,
    player2_launcher_id INT,
    stadium_id INT,
    winner_id INT,
    finish_type ENUM('Draw', 'Survivor', 'KO', 'Burst', 'Extreme'),
    end_time TIMESTAMP,
    draw TINYINT(1) DEFAULT 0,
    start_time TIMESTAMP NULL,
    FOREIGN KEY (tournament_id) REFERENCES Tournaments(tournament_id),
    FOREIGN KEY (player1_id) REFERENCES Players(player_id),
    FOREIGN KEY (player2_id) REFERENCES Players(player_id),
    FOREIGN KEY (player1_combination_id) REFERENCES BeybladeCombinations(combination_id),
    FOREIGN KEY (player2_combination_id) REFERENCES BeybladeCombinations(combination_id),
    FOREIGN KEY (player1_launcher_id) REFERENCES Launchers(launcher_id),
    FOREIGN KEY (player2_launcher_id) REFERENCES Launchers(launcher_id),
    FOREIGN KEY (winner_id) REFERENCES Players(player_id),
    FOREIGN KEY (stadium_id) REFERENCES Stadiums(stadium_id)
);

-- TournamentParticipant table (updated for Player/Combination participation & ELO)
CREATE TABLE IF NOT EXISTS TournamentParticipant (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT,
    player_id INT,
    combination_id INT,
    participant_type ENUM('Player', 'Combination'),
    seed INT,
    elo_rating INT DEFAULT 1000,  -- Default ELO rating
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    FOREIGN KEY (tournament_id) REFERENCES Tournaments(tournament_id),
    FOREIGN KEY (player_id) REFERENCES Players(player_id),
    FOREIGN KEY (combination_id) REFERENCES BeybladeCombinations(combination_id),
    CONSTRAINT chk_participant_type CHECK (
        (participant_type = 'Player' AND combination_id IS NULL AND player_id IS NOT NULL) OR 
        (participant_type = 'Combination' AND player_id IS NULL AND combination_id IS NOT NULL)
    )
);

GRANT ALL PRIVILEGES ON beyblade_db.* TO 'beyblade_user'@'%' IDENTIFIED BY 'Sample_DB_Password';
FLUSH PRIVILEGES;