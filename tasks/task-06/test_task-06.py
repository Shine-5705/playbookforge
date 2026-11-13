from solution import parse_ints

def test_parse():
    assert parse_ints('1, 2 ,3')==[1,2,3]
