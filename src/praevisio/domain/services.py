from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Tuple

from .entities import Hook, HookResult, CommitContext
from .value_objects import HookType, ExitCode


class HookSelectionService:
    """Selects and orders hooks based on type, file patterns, and dependencies."""

    def filter_by_type(self, hooks: Iterable[Hook], hook_type: HookType) -> List[Hook]:
        return [h for h in hooks if h.enabled and h.type == hook_type]

    def sort_by_dependencies(self, hooks: List[Hook]) -> List[Hook]:
        # Simple topological sort (Kahn's algorithm)
        id_to_hook = {h.id: h for h in hooks}
        incoming = {h.id: set(h.depends_on) for h in hooks}
        dependents: Dict[str, List[str]] = {h.id: [] for h in hooks}
        for hook in hooks:
            for dep in hook.depends_on:
                if dep in dependents:
                    dependents[dep].append(hook.id)

        ready = deque([h.id for h in hooks if not incoming[h.id]])
        order: List[Hook] = []
        ordered_ids = set()
        while ready:
            hid = ready.popleft()
            if hid in ordered_ids:
                continue
            order.append(id_to_hook[hid])
            ordered_ids.add(hid)
            for child in dependents.get(hid, []):
                deps = incoming[child]
                if hid in deps:
                    deps.remove(hid)
                if not deps and child not in ordered_ids:
                    ready.append(child)
        # Append any remaining hooks (in case of cycles, keep original order)
        remaining = [h for h in hooks if h.id not in ordered_ids]
        return order + remaining

    def matched_files(self, hook: Hook, context: CommitContext) -> List[str]:
        if not hook.file_scoped:
            return context.staged_files
        if not hook.patterns:
            return context.staged_files
        matched = []
        for f in context.staged_files:
            if any(p.matches(f) for p in hook.patterns):
                matched.append(f)
        return matched
