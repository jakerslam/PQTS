"""Deterministic runtime module registry and lifecycle manager."""

from __future__ import annotations

from collections import OrderedDict, deque
from typing import Dict

from contracts import ModuleHealth, RuntimeContext, RuntimeModule


class ModuleRegistry:
    """Owns module registration, dependency validation, and lifecycle ordering."""

    def __init__(self) -> None:
        self._modules: "OrderedDict[str, RuntimeModule]" = OrderedDict()
        self._start_order: list[str] = []

    def register(self, module: RuntimeModule) -> None:
        name = module.descriptor.name
        if not name:
            raise ValueError("module descriptor.name cannot be empty")
        if name in self._modules:
            raise ValueError(f"module '{name}' is already registered")
        self._modules[name] = module

    def register_many(self, modules: list[RuntimeModule]) -> None:
        for module in modules:
            self.register(module)

    @property
    def modules(self) -> Dict[str, RuntimeModule]:
        return dict(self._modules)

    def resolve_start_order(self) -> list[str]:
        if not self._modules:
            return []

        graph: dict[str, set[str]] = {name: set() for name in self._modules}
        indegree: dict[str, int] = {name: 0 for name in self._modules}

        for name, module in self._modules.items():
            for dependency in module.descriptor.requires:
                if dependency not in self._modules:
                    raise ValueError(
                        f"module '{name}' depends on unknown module '{dependency}'"
                    )
                if name not in graph[dependency]:
                    graph[dependency].add(name)
                    indegree[name] += 1

        queue = deque(sorted([name for name, count in indegree.items() if count == 0]))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in sorted(graph[node]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._modules):
            unresolved = sorted(name for name, degree in indegree.items() if degree > 0)
            raise ValueError(f"cyclic module dependency detected: {unresolved}")

        self._start_order = order
        return list(order)

    async def start_all(self, context: RuntimeContext) -> list[str]:
        order = self.resolve_start_order()
        started: list[str] = []
        try:
            for name in order:
                await self._modules[name].start(context)
                started.append(name)
        except Exception:
            # Best effort rollback for already started modules.
            for started_name in reversed(started):
                await self._modules[started_name].stop(context)
            self._start_order = []
            raise

        self._start_order = started
        return list(started)

    async def stop_all(self, context: RuntimeContext) -> list[str]:
        order = list(reversed(self._start_order or self.resolve_start_order()))
        stopped: list[str] = []
        for name in order:
            await self._modules[name].stop(context)
            stopped.append(name)
        self._start_order = []
        return stopped

    def health_snapshot(self) -> dict[str, ModuleHealth]:
        return {name: module.health() for name, module in self._modules.items()}
