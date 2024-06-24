import random
from typing import Any


class Machine:
    DEEPSLEEP = "deepsleep"
    SLEEP = "sleep"
    IDLE = "idle"


class Pin:
    OUT = "output-pin"
    IN = "input-pin"
    PULL_UP = "pull-up"
    PULL_DOWN = "pull-down"
    IRQ_FALLING = "irq-falling"

    def __init__(
            self,
            id: Any, # noqa
            mode: str = None,
            value: int = None,
            pull: str = None):
        self.id = id
        self.mode = mode
        self._value: int = value
        self.pull = pull

    def value(self) -> int:
        if self.mode == self.IN:
            if self._value is not None:
                print(f"{self.id} is {self._value} (IN)")
                return self._value
            else:
                random_int = random.choice(range(0, 1024))
                if random_int > 900:
                    print(f"{self.id} is high (random IN)")
                    return 1
                else:
                    print(f"{self.id} is low (random IN)")
                    return 0
        else:
            print(f"{self.id} is {self._value} (OUT)")
            return self._value

    def high(self):
        print(f"{self.id} is high (OUT)")
        self._value = 1

    def low(self):
        print(f"{self.id} is low (OUT)")
        self._value = 0

    def toggle(self):
        if self._value == 0:
            print(f"{self.id} was low (OUT) (will toggle to high)")
            self.high()
        else:
            print(f"{self.id} was high (OUT) (will toggle to low)")
            self.low()

    def irq(self, trigger=None, handler=None, wake=None):  # noqa
        print(f"IRQ trigger: {trigger}, handler: {handler}, wake: {wake}")
