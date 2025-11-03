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
"""A light-weight pydantic-like loader for dataclasses.

Avoids dependency on pydantic, is lightweight, and has some important differences -

- Automatically loads nested dataclasses, enums, etc.
- The only type which is implicitly cast is list ["a", 1] to ("a", 1) when needed.
"""

import dataclasses
import enum
import logging
from types import UnionType

import typing
from typing import Any, Type, TypeVar

_T = TypeVar("_T", bound=Any)
_U = TypeVar("_U")


class _TypeError(TypeError):
    pass


class UnknownFieldsError(TypeError):
    """Some fields were not in the dataclass being loaded."""

    pass


# Note: While this works with unions, pyright does not handle type checking and can flag
# it as an error.
def as_type(typ: Type[_U], value: Any) -> _U:
    """Generic converter from json-read value to a strict type.

    Args:
      type: Can be list, tuple, dict, enum, dataclass.
      value: Something that was json.load()-ed.

    Returns:
      A value that now conforms to the data type requested.
    """
    if dataclasses.is_dataclass(typ):
        return load_dataclass(typ, value)  # type: ignore

    if typ is float and isinstance(value, int):
        # Special case - allow int to be loaded as float.
        return float(value)  # type: ignore

    origin = typing.get_origin(typ)

    if origin is list:
        return [as_type(typing.get_args(typ)[0], v) for v in value]  # type: ignore
    elif origin is tuple:
        if len(value) != len(typing.get_args(typ)):
            raise _TypeError(f"Length mismatch loading {value=} as type {typ=}")
        return tuple(as_type(t, v) for t, v in zip(typing.get_args(typ), value))  # type: ignore
    elif origin is dict:
        return {k: as_type(typing.get_args(typ)[1], v) for k, v in value.items()}  # type: ignore
    elif origin is set:
        return {as_type(typing.get_args(typ)[0], v) for v in value}  # type: ignore
    elif origin is UnionType:
        for typ in typing.get_args(typ):
            try:
                return as_type(typ, value)
            except TypeError:
                continue
        raise _TypeError(f"Could not load {value=} as union type {typ=}")
    elif issubclass(typ, enum.Enum):  # type: ignore
        # Handle enum.
        try:
            return typ[value]  # Or type(value) also works for enum.
        except (ValueError, KeyError) as exc:
            raise _TypeError(f"Could not load {value=} as enum {typ=}") from exc

    if not isinstance(value, typ):
        raise _TypeError(f"Could not load {value=} as type {typ=}")
    return value  # type: ignore


def load_dataclass(
    dataclass_type: Type[_T], data: dict[str, Any], ignore_unknown_fields: bool = False
) -> _T:
    """Loads json into dataclass recursively.

    Identifies and loads all subfields which are also dataclasses.
    """
    fields_dict: dict[str, Any] = {}
    for field in dataclasses.fields(dataclass_type):
        if field.name not in data:
            # Will attempt to instantiate with default.
            continue
        fields_dict[field.name] = as_type(
            field.type,  # type: ignore
            data[field.name],
        )
    unseen_fields = set(data.keys()) - set(fields_dict.keys())
    if unseen_fields:
        unknown_fields_dict = {k: data[k] for k in unseen_fields}
        if ignore_unknown_fields:
            logging.warning(
                f"Unknown fields ignored: {unknown_fields_dict} for {dataclass_type.__name__}"
            )
        else:
            raise UnknownFieldsError(
                f"Unknown fields: {unknown_fields_dict} for {dataclass_type=}"
            )
    return dataclass_type(**fields_dict)
