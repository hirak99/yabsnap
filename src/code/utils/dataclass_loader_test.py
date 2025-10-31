import dataclasses
import enum
import unittest

from . import dataclass_loader

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class _TestEnum(enum.Enum):
    FOO = "FOO"
    BAR = "BAR"


@dataclasses.dataclass
class _NestedClass:
    x: int


@dataclasses.dataclass
class _TestClass:
    x_list: list[int] = dataclasses.field(default_factory=list)
    nested: None | _NestedClass = None
    x_tuple: tuple[str, int] | None = None
    x_enum: _TestEnum | None = None


class DataclassLoaderTest(unittest.TestCase):
    def test_simple_load(self):
        test = dataclass_loader.load_from_dict(_TestClass, {"x_list": [1, 2, 3]})
        self.assertEqual(test, _TestClass(x_list=[1, 2, 3]))

    def test_nested_load(self):
        test = dataclass_loader.load_from_dict(_TestClass, {"nested": {"x": 1}})
        self.assertEqual(test, _TestClass(nested=_NestedClass(x=1)))

    def test_tuple(self):
        test = dataclass_loader.load_from_dict(_TestClass, {"x_tuple": ["a", 1]})
        self.assertEqual(test, _TestClass(x_tuple=("a", 1)))

    def test_enum(self):
        test = dataclass_loader.load_from_dict(_TestClass, {"x_enum": "FOO"})
        self.assertEqual(test, _TestClass(x_enum=_TestEnum.FOO))

    def test_errors(self):
        invalid_values = [
            (True, {"x_tuple": ["a", 1]}),
            (True, {"x_tuple": None}),
            (False, {"x_tuple": ["a", "b"]}),  # Typle is tuple[str, int].
            (False, {"x_tuple": ["a"]}),
            (False, {"x_tuple": ["a", 1, 2]}),
            (True, {"x_list": []}),
            (False, {"x_list": None}),  # Can be unspecified, but cannot be None.
            (True, {"nested": None}),
            (True, {"nested": {"x": 1}}),
            (False, {"nested": {}}),  # Mandatory field omitted from _NestedClass.
            (True, {"x_enum": "BAR"}),
            (False, {"x_enum": ""}),  # Invalid enum value.
        ]
        for is_valid, value in invalid_values:
            with self.subTest(expected_valid=is_valid, value=value):
                match is_valid:
                    case True:
                        _ = dataclass_loader.load_from_dict(_TestClass, value)
                    case False:
                        with self.assertRaises(TypeError, msg=value):
                            _ = dataclass_loader.load_from_dict(_TestClass, value)


if __name__ == "__main__":
    unittest.main()
