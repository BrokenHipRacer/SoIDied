import secrets
from dataclasses import dataclass

from src.api.route_registry import ROTATABLE_ROUTES, RouteSpec


@dataclass(frozen=True)
class RotatedRoute:
    spec: RouteSpec
    path: str

    def route_lines(self) -> list[str]:
        return [f'{method} {self.path}' for method in self.spec.methods]


def generate_rotated_path(used_paths: set[str]) -> str:
    while True:
        path = f'/api/v1/{secrets.token_urlsafe(32)}'
        if path not in used_paths:
            return path


def build_rotation() -> tuple[RotatedRoute, ...]:
    used_paths: set[str] = set()
    rotated: list[RotatedRoute] = []
    for spec in ROTATABLE_ROUTES:
        path = generate_rotated_path(used_paths)
        used_paths.add(path)
        rotated.append(RotatedRoute(spec=spec, path=path))
    return tuple(rotated)
