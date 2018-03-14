from inspect import isclass
from aioorm.ast.node import Node
from aioorm.ast.entity import Entity


def is_model(obj):
    if isclass(obj):
        return issubclass(obj, Model)
    return False


def ensure_tuple(value):
    if value is not None:
        return value if isinstance(value, (list, tuple)) else (value,)


def ensure_entity(value):
    if value is not None:
        return value if isinstance(value, Node) else Entity(value)
