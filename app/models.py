from sqlalchemy import Column, Integer, String, Enum, ForeignKey, CheckConstraint, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
#from base import Base

Base = declarative_base()

class Player(Base):
    __tablename__ = "Players"

    player_id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String(255), unique=True)

    # Matches as player 1
    player1_matches = relationship("Match", backref="player1")

    # Matches as player 2
    player2_matches = relationship("Match", backref="player2")

    # Tournaments participated in (Player)
    player_tournaments = relationship(
        "TournamentParticipant", foreign_keys="[TournamentParticipant.player_id]"
    )

class Blade(Base):
    __tablename__ = "Blades"

    blade_id = Column(Integer, primary_key=True, autoincrement=True)
    blade_name = Column(String(255), unique=True)
    canonical_name = Column(String(255))
    blade_type = Column(Enum("Attack", "Defense", "Stamina", "Balance", "None"))
    spin_direction = Column(Enum("Right-Spin", "Left-Spin", "Dual-Spin"))
    blade_weight = Column(Decimal(4, 1))

    # Combinations this blade is part of
    combinations = relationship("BeybladeCombination", backref="blade")

class Ratchet(Base):
    __tablename__ = "Ratchets"

    ratchet_id = Column(Integer, primary_key=True, autoincrement=True)
    ratchet_name = Column(String(255), unique=True)
    ratchet_protrusions = Column(Integer)
    ratchet_height = Column(Integer)
    ratchet_weight = Column(Decimal(4, 1))

    # Combinations this ratchet is part of
    combinations = relationship("BeybladeCombination", backref="ratchet")

class Bit(Base):
    __tablename__ = "Bits"

    bit_id = Column(Integer, primary_key=True, autoincrement=True)
    bit_name = Column(String(255), unique=True)
    full_bit_name = Column(String(255))
    bit_weight = Column(Decimal(4, 1))
    bit_type = Column(Enum("Attack", "Defense", "Stamina", "Balance", "Unknown"), default="Unknown")

    # Stats for this bit
    stats = relationship("BitStats", uselist=False, backref="bit")

    # Combinations this bit is part of
    combinations = relationship("BeybladeCombination", backref="bit")

class BitStats(Base):
    __tablename__ = "BitStats"

    bit_id = Column(Integer, ForeignKey("Bits.bit_id"), primary_key=True)
    attack = Column(Integer, default=0)
    defense = Column(Integer, default=0)
    stamina = Column(Integer, default=0)
    dash = Column(Integer, default=0)
    burst_resistance = Column(Integer, default=0)

class BladeStats(Base):
    __tablename__ = "BladeStats"

    blade_id = Column(Integer, ForeignKey("Blades.blade_id"), primary_key=True)
    attack = Column(Integer, default=0)
    defense = Column(Integer, default=0)
    stamina = Column(Integer, default=0)
    weight = Column(Decimal(4, 1))

class RatchetStats(Base):
    __tablename__ = "RatchetStats"

    ratchet_id = Column(Integer, ForeignKey("Ratchets.ratchet_id"), primary_key=True)
    attack = Column(Integer, default=0)
    defense = Column(Integer, default=0)
    stamina = Column(Integer, default=0)
    height = Column(Integer, default=0)

class BladeAlias(Base):
    __tablename__ = "BladeAliases"

    alias_id = Column(Integer, primary_key=True, autoincrement=True)
    blade_id = Column(Integer, ForeignKey("Blades.blade_id"))
    alias_name = Column(String(255), unique=True)

class BeybladeCombination(Base):
    __tablename__ = "BeybladeCombinations"
    combination_id = Column(Integer, primary_key=True, autoincrement=True)
    blade_id = Column(Integer, ForeignKey("Blades.blade_id"))
    ratchet_id = Column(Integer, ForeignKey("Ratchets.ratchet_id"))
    bit_id = Column(Integer, ForeignKey("Bits.bit_id"))
    combination_name = Column(String(255), unique=True)
    combination_type = Column(Enum("Attack", "Defense", "Stamina", "Balance", "Unknown"))
    combination_weight = Column(DECIMAL(5, 2))

    combination1_matches = relationship("Match", foreign_keys="[Match.combination1_id]", backref="combination1")
    combination2_matches = relationship("Match", foreign_keys="[Match.combination2_id]", backref="combination2")

    combination_tournaments = relationship(
        "TournamentParticipant", foreign_keys="[TournamentParticipant.combination_id]"
    )

class LauncherClass(Base):
    __tablename__ = "LauncherClasses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(String(255))
    launchers = relationship("Launcher", backref="launcher_class")

class Launcher(Base):
    __tablename__ = "Launchers"
    launcher_id = Column(Integer, primary_key=True, autoincrement=True)
    launcher_name = Column(String(255), unique=True)
    launcher_class_id = Column(Integer, ForeignKey("LauncherClasses.id"))
    player1_matches = relationship("Match", foreign_keys="[Match.player1_launcher_id]", backref="player1_launcher")
    player2_matches = relationship("Match", foreign_keys="[Match.player2_launcher_id]", backref="player2_launcher")

class LauncherClassSpinCompatibility(Base):
    __tablename__ = "LauncherClassSpinCompatibility"
    launcher_class_id = Column(Integer, ForeignKey("LauncherClasses.id"), primary_key=True)
    spin_direction = Column(Enum("Right-Spin", "Left-Spin", "Dual-Spin"), primary_key=True)

class Stadium(Base):
    __tablename__ = "Stadiums"
    stadium_id = Column(Integer, primary_key=True, autoincrement=True)
    stadium_name = Column(String(255), nullable=False, unique=True)
    stadium_class = Column(String(255), nullable=False)
    matches = relationship("Match", backref="stadium")

class Match(Base):
    __tablename__ = "Matches"
    match_id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, ForeignKey("Tournaments.tournament_id"))
    player1_id = Column(Integer, ForeignKey("Players.player_id"))
    player2_id = Column(Integer, ForeignKey("Players.player_id"))
    combination1_id = Column(Integer, ForeignKey("BeybladeCombinations.combination_id"))
    combination2_id = Column(Integer, ForeignKey("BeybladeCombinations.combination_id"))
    player1_launcher_id = Column(Integer, ForeignKey("Launchers.launcher_id"))
    player2_launcher_id = Column(Integer, ForeignKey("Launchers.launcher_id"))
    stadium_id = Column(Integer, ForeignKey("Stadiums.stadium_id"))
    winner_id = Column(Integer, ForeignKey("Players.player_id"))
    finish_type = Column(Enum('Draw', 'Survivor', 'KO', 'Burst', 'Extreme'))
    end_time = Column(TIMESTAMP)
    draw = Column(Boolean)
    start_time = Column(TIMESTAMP)

class Tournament(Base):
    __tablename__ = "Tournaments"
    tournament_id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_name = Column(String(255))
    start_date = Column(TIMESTAMP)
    end_date = Column(TIMESTAMP)
    tournament_type = Column(Enum("Standard", "PlayerLadder", "CombinationLadder"), default="Standard")
    participants = relationship("TournamentParticipant", back_populates="tournament")
    matches = relationship("Match", back_populates="tournament")

class TournamentParticipant(Base):
    __tablename__ = "TournamentParticipant"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, ForeignKey("Tournaments.tournament_id"))
    player_id = Column(Integer, ForeignKey("Players.player_id"))
    combination_id = Column(Integer, ForeignKey("BeybladeCombinations.combination_id"))
    participant_type = Column(Enum("Player", "Combination"))
    seed = Column(Integer)
    elo_rating = Column(Integer, default=1000)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    tournament = relationship("Tournament", back_populates="participants")
    player = relationship("Player", back_populates="player_tournaments")
    combination = relationship("BeybladeCombination", back_populates="combination_tournaments")

    __table_args__ = (
        CheckConstraint(
            "(participant_type = 'Player' AND combination_id IS NULL AND player_id IS NOT NULL) OR "
            "(participant_type = 'Combination' AND player_id IS NULL AND combination_id IS NOT NULL)",
            name="chk_participant_type",
        ),
    )