from typing import TypeVar, Callable

K = TypeVar('K')
V = TypeVar('V')

class QueryDict(dict[K, V]):
  def __init__(self, default: Callable[[K], V]):
    self.default = default
  
  def __missing__(self, key: K) -> V:
    # expensive computations
    val = self.default(key)
    self[key] = val
    return val
