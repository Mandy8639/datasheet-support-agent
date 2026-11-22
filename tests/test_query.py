import pytest

from datasheet_agent.retrieval.query import understand


@pytest.mark.parametrize(
    ("question", "skus"),
    [
        ("What's the max VIN of the Arduino UNO R4 WiFi?", ["ABX00087"]),
        ("UNO R4 Minima operating temperature", ["ABX00080"]),
        ("Nano 33 BLE Rev2 flash size", ["ABX00071"]),  # not also Nano 33 BLE
        ("Nano 33 BLE power", ["ABX00030"]),
        ("Compare the GIGA R1 WiFi and the UNO R4 WiFi", ["ABX00063", "ABX00087"]),
        ("pins on the ABX00028", ["ABX00028"]),
        ("Portenta Max Carrier power jack", ["ABX00043"]),
        ("Portenta X8 vs Portenta C33", ["ABX00049", "ABX00074"]),
    ],
)
def test_finds_boards(question, skus):
    assert sorted(understand(question).skus) == sorted(skus)


@pytest.mark.parametrize(
    ("question", "mention"),
    [
        ("Operating temperature of the Arduino Portenta H7?", "portenta h7"),
        ("Input voltage range of the Arduino Nano Matter?", "nano matter"),
        ("What supply voltage does the Raspberry Pi Pico need?", "raspberry pi pico"),
    ],
)
def test_flags_boards_not_in_corpus(question, mention):
    info = understand(question)
    assert info.skus == []
    assert any(mention in m for m in info.unknown_mentions)


def test_known_board_is_not_reported_unknown():
    assert understand("Max VIN of the Nano ESP32?").unknown_mentions == []


def test_extra_aliases_for_fixtures():
    info = understand(
        "Max VIN of Test Board INJ-1?", extra_aliases=(("Test Board INJ-1", "ZZTINJ1"),)
    )
    assert info.skus == ["ZZTINJ1"]


def test_strip_boards_removes_every_board_name():
    from datasheet_agent.retrieval.query import strip_boards

    q = "Which accepts a higher maximum VIN, the UNO R4 WiFi or the GIGA R1 WiFi?"
    assert strip_boards(q) == "which accepts a higher maximum vin the or the"
