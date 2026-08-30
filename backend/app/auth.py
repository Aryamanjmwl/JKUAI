from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    user_id: str
    groups: tuple[str, ...]


def can_access(visibility: str, allowed_groups: list[str], user: UserContext) -> bool:
    return visibility == "public" or bool(set(allowed_groups).intersection(user.groups))
