# Copyright 2025 Arnab Bose
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
    nested_list: list[_NestedClass] = dataclasses.field(default_factory=list)


class DataclassLoaderTest(unittest.TestCase):
    def test_simple_load(self):
        test = dataclass_loader.load_dataclass(_TestClass, {"x_list": [1, 2, 3]})
        self.assertEqual(test, _TestClass(x_list=[1, 2, 3]))

    def test_nested_dc(self):
        test = dataclass_loader.load_dataclass(_TestClass, {"nested": {"x": 1}})
        self.assertEqual(test, _TestClass(nested=_NestedClass(x=1)))

    def test_dataclass_list(self):
        test = dataclass_loader.load_dataclass(
            _TestClass, {"nested_list": [{"x": 1}, {"x": 2}]}
        )
        self.assertEqual(
            test,
            _TestClass(
                nested_list=[
                    _NestedClass(x=1),
                    _NestedClass(x=2),
                ]
            ),
        )

    def test_tuple(self):
        test = dataclass_loader.load_dataclass(_TestClass, {"x_tuple": ["a", 1]})
        self.assertEqual(test, _TestClass(x_tuple=("a", 1)))

    def test_enum(self):
        test = dataclass_loader.load_dataclass(_TestClass, {"x_enum": "FOO"})
        self.assertEqual(test, _TestClass(x_enum=_TestEnum.FOO))

    def test_dataclass_errors(self):
        # These will be attempted to be loaded as _TestClass.
        # The boolean indicates if expected to be parsed without error, or not.
        values_to_check = [
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
        for is_valid, value in values_to_check:
            with self.subTest(expected_valid=is_valid, value=value):
                match is_valid:
                    case True:
                        _ = dataclass_loader.load_dataclass(_TestClass, value)  # type: ignore
                    case False:
                        with self.assertRaises(TypeError, msg=value):
                            _ = dataclass_loader.load_dataclass(_TestClass, value)  # type: ignore

    def test_as_type_works_as_expected(self):
        self.assertEqual(dataclass_loader.as_type(int, 1), 1)
        self.assertEqual(dataclass_loader.as_type(list[int], [1, 2]), [1, 2])
        self.assertEqual(dataclass_loader.as_type(int | str, 1), 1)  # type: ignore
        self.assertEqual(dataclass_loader.as_type(int | str, "1"), "1")  # type: ignore
        self.assertEqual(dataclass_loader.as_type(dict[str, int], {"a": 1}), {"a": 1})
        # Special case - allow int to be loaded as float.
        self.assertEqual(dataclass_loader.as_type(float, 1), 1)
        self.assertEqual(dataclass_loader.as_type(float, 1.2), 1.2)

    def test_as_type_expected_failure_cases(self):
        cases = [
            (int | str, []),
            (int, 1.2),
            (int, "1.2"),
        ]
        for typ, value in cases:
            with self.subTest(typ=typ, value=value):
                with self.assertRaises(TypeError):
                    dataclass_loader.as_type(typ, value)  # type: ignore

    def test_error_on_unknown_fields(self):
        with self.assertRaises(dataclass_loader.UnknownFieldsError):
            dataclass_loader.load_dataclass(_TestClass, {"unknown": 1})

        # Check that error is suppressed.
        result = dataclass_loader.load_dataclass(
            _TestClass, {"unknown": 1}, ignore_unknown_fields=True
        )
        self.assertEqual(result, _TestClass())


if __name__ == "__main__":
    unittest.main()
