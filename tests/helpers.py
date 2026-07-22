from pga_shootout.models import Bag, BagEntry, Club, GameState, Stats


def make_game_state() -> GameState:
    club = Club(
        identifier="fixture-club",
        name="Fixture Club",
        brand="Fixture Brand",
        club_type="driver",
        stats_by_level={1: Stats(power=10, control=20, spin=30)},
    )
    return GameState(bag=Bag((BagEntry(club, 1),)), current_club_id=club.identifier)
