import logging
from typing import List

from fastapi import Depends, HTTPException, Request, status

from src.database.models import Role, User
from src.services.auth import get_current_user

logger = logging.getLogger(__name__)


class RoleAccess:
    def __init__(self, allowed_roles: List[Role]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, request: Request, current_user: User = Depends(get_current_user)
    ):
        logger.debug(
            "%s %s | user role: %s | allowed: %s",
            request.method,
            request.url,
            current_user.roles,
            self.allowed_roles,
        )
        if current_user.roles not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Operation forbidden"
            )
