from evals.rejections import categorise


def test_categorise_shapes():
    assert categorise("2 unsupported claim(s) dropped; Signed in unmet with p=0.91") == (
        "process_unmet",
        "Signed in",
    )
    assert categorise("Password entered unmet with p=0.8") == ("process_unmet", "Password entered")
    assert categorise("Exception name reported unmet with p=0.81") == (
        "outcome_unmet",
        "Exception name reported",
    )
    assert categorise("uncertain: complete p=0.62, max unmet p=0.50")[0] == "uncertain"
    assert (
        categorise(
            "answer carries no fact found on the page (1 unsupported, rest narrative); complete p=0.5"
        )[0]
        == "no_fact"
    )
