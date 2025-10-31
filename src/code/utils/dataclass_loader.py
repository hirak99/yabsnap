import dataclasses
import enum
from types import UnionType

import typing
from typing import Any, Type, TypeVar

_T = TypeVar("_T", bound=Any)


class _TypeError(TypeError):
    pass


def _as_type(typ, value: Any):
    if dataclasses.is_dataclass(typ):
        return load_from_dict(typ, value)  # type: ignore
    origin = typing.get_origin(typ)

    # Handle enums
    if isinstance(typ, type) and issubclass(typ, enum.Enum):
        # Try to convert value to enum member
        try:
            return typ(value)  # or typ[value] if the value is a valid key for the enum
        except ValueError:
            raise _TypeError(f"Could not load {value=} as enum {typ=}")

    if origin is list:
        return [_as_type(typing.get_args(typ)[0], v) for v in value]
    elif origin is tuple:
        if len(value) != len(typing.get_args(typ)):
            raise _TypeError(f"Length mismatch loading {value=} as type {typ=}")
        return tuple(_as_type(t, v) for t, v in zip(typing.get_args(typ), value))
    elif origin is dict:
        return {k: _as_type(typing.get_args(typ)[1], v) for k, v in value.items()}
    elif origin is set:
        return {_as_type(typing.get_args(typ)[0], v) for v in value}

    if not isinstance(value, typ):
        raise _TypeError(f"Could not load {value=} as type {typ=}")
    return value


def load_from_dict(dataclass_type: Type[_T], data: dict[str, Any]) -> _T:
    """Loads json into dataclass recursively.

    Identifies and loads all subfields which are also dataclasses.
    """
    fields_dict = {}
    for field in dataclasses.fields(dataclass_type):
        if field.name not in data:
            # Will attempt to instantiate with default.
            continue
        origin = typing.get_origin(field.type)
        value = data[field.name]
        if origin is UnionType:
            # If it is a Union type, load as the first dataclass if there is any.
            # Primarily for dataclass | None.
            for typ in typing.get_args(field.type):
                try:
                    fields_dict[field.name] = _as_type(typ, value)
                    break
                except TypeError:
                    # Try all union types to see which one matches.
                    continue
            else:
                raise _TypeError(f"Could not load {value=} as type {field.type=}")
        else:
            fields_dict[field.name] = _as_type(
                field.type,  # type: ignore
                data[field.name],
            )
    return dataclass_type(**fields_dict)
