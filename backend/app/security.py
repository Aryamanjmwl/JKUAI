from fastapi import Header

from .auth import UserContext
from .config import get_settings


def build_user_context(
    user_id: str,
    user_groups: str,
    *,
    demo_roles_enabled: bool,
) -> UserContext:
    if not demo_roles_enabled:
        return UserContext(user_id="anonymous", groups=())

    groups = tuple(sorted({group.strip() for group in user_groups.split(",") if group.strip()}))
    return UserContext(user_id=user_id, groups=groups)


async def get_user_context(
    x_user_id: str = Header(default="anonymous"),
    x_user_groups: str = Header(default=""),
) -> UserContext:
    return build_user_context(
        x_user_id,
        x_user_groups,
        demo_roles_enabled=get_settings().enable_demo_roles,
    )
