-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS beyblade_db;

-- Use the database
USE beyblade_db;

-- Create the Players table
CREATE TABLE IF NOT EXISTS Players (
    player_id INT AUTO_INCREMENT PRIMARY KEY,
    player_name VARCHAR(255) UNIQUE
);

-- Create the Blades table
CREATE TABLE IF NOT EXISTS Blades (
    blade_id INT AUTO_INCREMENT PRIMARY KEY,
    blade_name VARCHAR(255) UNIQUE,
    canonical_name VARCHAR(255),
    blade_type ENUM('Attack', 'Defense', 'Stamina', 'Balance', 'None'),
    spin_direction ENUM('Right-Spin', 'Left-Spin', 'Dual-Spin'),
    blade_weight DECIMAL(4, 1) NULL
);

-- Create the Ratchets table
CREATE TABLE IF NOT EXISTS Ratchets (
    ratchet_id INT AUTO_INCREMENT PRIMARY KEY,
    ratchet_name VARCHAR(255) UNIQUE,
    ratchet_protrusions INT,
    ratchet_height INT,
    ratchet_weight DECIMAL(4, 1) NULL
);

-- Modify the Bits table to add full_bit_name and bit_type
CREATE TABLE IF NOT EXISTS Bits (
    bit_id INT AUTO_INCREMENT PRIMARY KEY,
    bit_name VARCHAR(255) UNIQUE,
    full_bit_name VARCHAR(255),
    bit_weight DECIMAL(4, 1) NULL,
    bit_type ENUM('Attack', 'Defense', 'Stamina', 'Balance', 'Unknown') DEFAULT 'Unknown' -- Added bit_type
);

-- No longer needed: Drop the Stats table
DROP TABLE IF EXISTS Stats;

-- Modify the BitStats table (simplified)
CREATE TABLE IF NOT EXISTS BitStats (
    bit_id INT PRIMARY KEY,  -- bit_id is now the sole primary key
    attack DECIMAL(5, 2) DEFAULT NULL,
    defense DECIMAL(5, 2) DEFAULT NULL,
    stamina DECIMAL(5, 2) DEFAULT NULL,
    dash DECIMAL(5, 2) DEFAULT NULL,
    burst_resistance DECIMAL(5, 2) DEFAULT NULL,
    FOREIGN KEY (bit_id) REFERENCES Bits(bit_id)
);

-- Modify the BladeStats table (simplified)
CREATE TABLE IF NOT EXISTS BladeStats (
    blade_id INT PRIMARY KEY,
    attack DECIMAL(5, 2) DEFAULT NULL,
    defense DECIMAL(5, 2) DEFAULT NULL,
    stamina DECIMAL(5, 2) DEFAULT NULL,
    weight DECIMAL(5, 2) DEFAULT NULL,
    FOREIGN KEY (blade_id) REFERENCES Blades(blade_id)
);

-- Modify the RatchetStats table (simplified)
CREATE TABLE IF NOT EXISTS RatchetStats (
    ratchet_id INT PRIMARY KEY,
    attack DECIMAL(5, 2) DEFAULT NULL,
    defense DECIMAL(5, 2) DEFAULT NULL,
    stamina DECIMAL(5, 2) DEFAULT NULL,
    click_strength DECIMAL(5, 2) DEFAULT NULL,
    FOREIGN KEY (ratchet_id) REFERENCES Ratchets(ratchet_id)
);

-- Create the BladeAliases table
CREATE TABLE IF NOT EXISTS BladeAliases (
    alias_id INT AUTO_INCREMENT PRIMARY KEY,
    blade_id INT,
    alias_name VARCHAR(255) UNIQUE,
    FOREIGN KEY (blade_id) REFERENCES Blades(blade_id)
);

-- Create the BeybladeCombinations table
CREATE TABLE IF NOT EXISTS BeybladeCombinations (
    combination_id INT AUTO_INCREMENT PRIMARY KEY,
    blade_id INT,
    ratchet_id INT,
    bit_id INT,
    combination_name VARCHAR(255) UNIQUE,
    combination_type ENUM('Attack', 'Defense', 'Stamina', 'Balance', 'Unknown'),
    combination_weight DECIMAL(5, 2) NULL,
    FOREIGN KEY (blade_id) REFERENCES Blades(blade_id),
    FOREIGN KEY (ratchet_id) REFERENCES Ratchets(ratchet_id),
    FOREIGN KEY (bit_id) REFERENCES Bits(bit_id)
);

-- Create the LauncherTypes table
CREATE TABLE IF NOT EXISTS LauncherTypes (
    launcher_id INT AUTO_INCREMENT PRIMARY KEY,
    launcher_name VARCHAR(255) UNIQUE
);

-- Create the Tournaments table
CREATE TABLE IF NOT EXISTS Tournaments (
    tournament_id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_name VARCHAR(255),
    start_date TIMESTAMP,
    end_date TIMESTAMP
);

-- Create the Matches table
CREATE TABLE IF NOT EXISTS Matches (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT,
    player1_id INT,
    player2_id INT,
    player1_combination_id INT,
    player2_combination_id INT,
    player1_launcher_id INT,
    player2_launcher_id INT,
    winner_id INT,
    finish_type ENUM('Draw', 'Survivor', 'KO', 'Burst', 'Extreme'),
    match_time TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES Tournaments(tournament_id),
    FOREIGN KEY (player1_id) REFERENCES Players(player_id),
    FOREIGN KEY (player2_id) REFERENCES Players(player_id),
    FOREIGN KEY (player1_combination_id) REFERENCES BeybladeCombinations(combination_id),
    FOREIGN KEY (player2_combination_id) REFERENCES BeybladeCombinations(combination_id),
    FOREIGN KEY (player1_launcher_id) REFERENCES LauncherTypes(launcher_id),
    FOREIGN KEY (player2_launcher_id) REFERENCES LauncherTypes(launcher_id),
    FOREIGN KEY (winner_id) REFERENCES Players(player_id)
);

GRANT ALL PRIVILEGES ON beyblade_db.* TO 'beyblade_user'@'%' IDENTIFIED BY 'Sample_DB_Password'; # For your app
FLUSH PRIVILEGES;