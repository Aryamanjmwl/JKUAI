from fastapi import Header

from .auth import UserContext


async def get_user_context(
    x_user_id: str = Header(default="anonymous"),
    x_user_groups: str = Header(default=""),
) -> UserContext:
    groups = tuple(sorted({g.strip() for g in x_user_groups.split(",") if g.strip()}))
    return UserContext(user_id=x_user_id, groups=groups)
