from dataclasses import dataclass
from typing import Type

from flask_restful import Resource

from src.api.check_in import CheckIn, CheckInStatus
from src.api.messages import MessageUpload
from src.api.utils_api import UtilsApi


@dataclass(frozen=True)
class RouteSpec:
    resource: Type[Resource]
    canonical_path: str
    methods: tuple[str, ...]
    endpoint: str


ROTATABLE_ROUTES: tuple[RouteSpec, ...] = (
    RouteSpec(CheckIn, '/api/v1/checkin', ('PUT',), 'checkin'),
    RouteSpec(CheckInStatus, '/api/v1/checkin/status', ('GET',), 'checkin_status'),
    RouteSpec(MessageUpload, '/api/v1/messages/add', ('POST',), 'messages_add'),
    RouteSpec(UtilsApi, '/api/v1/utils/api', ('GET',), 'utils_api'),
)

DARKMODE_CANONICAL_PATH = '/api/v1/darkmode'
DARKMODE_ENDPOINT = 'darkmode'


def canonical_route_lines() -> list[str]:
    return [f'{method} {spec.canonical_path}' for spec in ROTATABLE_ROUTES for method in spec.methods]
