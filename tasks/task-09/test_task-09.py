from solution import merge_counts

def test_merge():
    assert merge_counts({'a':1},{'a':2,'b':1})=={'a':3,'b':1}
