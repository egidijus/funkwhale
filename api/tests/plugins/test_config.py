import pytest

from funkwhale_api.plugins import config


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"test__test_value1": "hello"}, {"test__test_value1": "hello"}),
        (
            {"noop": "noop", "test__test_value1": "hello"},
            {"test__test_value1": "hello"},
        ),
        (
            {"test__test_value1": "hello", "test__test_value2": "world"},
            {"test__test_value1": "hello", "test__test_value2": "world"},
        ),
    ],
)
def test_validate_config(payload, expected):
    test_section = config.SettingSection("test")

    class TestSetting1(config.StringSetting):
        name = "test_value1"
        section = test_section
        default = ""

    class TestSetting2(config.StringSetting):
        name = "test_value2"
        section = test_section
        default = ""

    final = config.validate_config(payload, settings=[TestSetting1, TestSetting2])

    assert final == expected


def test_validate_config_boolean():
    test_section = config.SettingSection("test")

    class TestSetting(config.BooleanSetting):
        name = "test_value"
        section = test_section
        default = False

    final = config.validate_config({"test__test_value": True}, settings=[TestSetting])

    assert final == {"test__test_value": True}


def test_validate_config_number():
    test_section = config.SettingSection("test")

    class TestSetting(config.IntSetting):
        name = "test_value"
        section = test_section
        default = 12

    final = config.validate_config({"test__test_value": 12}, settings=[TestSetting])

    assert final == {"test__test_value": 12}
