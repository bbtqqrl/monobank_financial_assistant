from app.schemas.place import PlaceResponse
from app.services.place_matching import PlaceMethod, choose_place, names_match


def candidate(name, distance):
    return PlaceResponse(provider="google", place_id=name, name=name, category="cafe", address=None,
                         latitude=49.84, longitude=24.03, distance_m=distance)


def test_no_candidates():
    assert choose_place([], "KREDENS CAFE") == (None, PlaceMethod.NOT_FOUND)


def test_single_candidate_even_if_name_differs():
    only = candidate("Буденні бомбони", 20)
    assert choose_place([only], "ФОП Петренко О.І.") == (only, PlaceMethod.SINGLE)


def test_exactly_one_name_match_wins_over_nearest():
    neighbour, kredens = candidate("Буденні бомбони", 3), candidate("KREDENS CAFE на Валовій", 11)
    assert choose_place([neighbour, kredens], "KREDENS CAFE") == (kredens, PlaceMethod.NAME_MATCH)


def test_no_name_match_takes_nearest():
    far, near = candidate("Шаурма", 15), candidate("Кава", 4)
    assert choose_place([far, near], "ФОП Петренко О.І.") == (near, PlaceMethod.NEAREST)


def test_several_name_matches_take_nearest():
    first, second = candidate("SPAR", 12), candidate("SPAR Express", 6)
    assert choose_place([first, second], "SPAR") == (second, PlaceMethod.NEAREST)


def test_names_match_across_alphabets():
    assert names_match("McDonald’s", "Макдональдз")
    assert names_match("Аптека «Подорожник»", "Подорожник")
    assert names_match("ZABKA", "Żabka")
    assert names_match("Royal Kebab", "Роял Кебаб")


def test_names_do_not_match_on_noise():
    assert not names_match("ФОП Петренко О.І.", "Буденні бомбони")
    assert not names_match("SPAR", "STAR")
    assert not names_match("Кафе Аптека", "Кафе Аптека")
