"""蜂群（Hive）模拟器
模拟蜜蜂群体在蜂巢中的协作采集与生产行为。
用法: python scripts/hive_sim.py --population 30 --days 30
"""

import argparse
import random
import sys
from collections import defaultdict


class Bee:
    """单个蜜蜂个体。"""

    def __init__(self, bee_id: int, role: str = "worker") -> None:
        self.bee_id = bee_id
        self.role = role
        self.energy = 100.0
        self.carrying = 0.0

    @property
    def alive(self) -> bool:
        return self.energy > 0.0

    def act(self, nectar_field: float) -> float:
        """执行一次采集或生产动作，返回本次采集量。"""
        if self.role == "queen":
            self.energy = min(100.0, self.energy + 5.0)
            return 0.0
        if self.role == "drone":
            self.energy -= 1.0
            return 0.0
        gathered = min(nectar_field, random.uniform(0.5, 2.0))
        self.carrying += gathered
        self.energy -= 2.0
        return gathered

    def deposit(self) -> float:
        amount = self.carrying
        self.carrying = 0.0
        return amount

    def __repr__(self) -> str:
        return "Bee(id=%d, role=%s, energy=%.1f)" % (self.bee_id, self.role, self.energy)


class Hive:
    """蜂巢，管理整个蜂群的演化。"""

    def __init__(self, population: int = 30) -> None:
        self.population = population
        self.warehouse = 0.0
        self.day = 0
        self.bees = []
        self._spawn()

    def _spawn(self) -> None:
        for i in range(self.population):
            if i == 0:
                role = "queen"
            elif i % 7 == 0:
                role = "drone"
            else:
                role = "worker"
            self.bees.append(Bee(i, role))

    def step(self) -> None:
        self.day += 1
        nectar_field = max(0.0, 50.0 - 0.5 * self.day)
        for bee in self.bees:
            if bee.alive:
                bee.act(nectar_field)
        for bee in self.bees:
            self.warehouse += bee.deposit()
        self.bees = [b for b in self.bees if b.alive]
        if self.day % 10 == 0:
            self.bees.append(Bee(len(self.bees), "worker"))

    def report(self) -> dict:
        roles = defaultdict(int)
        for bee in self.bees:
            roles[bee.role] += 1
        return {
            "day": self.day,
            "alive": len(self.bees),
            "warehouse": round(self.warehouse, 2),
            "roles": dict(roles),
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="蜂群模拟器")
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    random.seed(args.seed)
    hive = Hive(args.population)
    for _ in range(args.days):
        hive.step()
    print("最终:", hive.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
