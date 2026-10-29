from uuid import uuid4
import pytest
from fastapi import HTTPException
from src.middlewares.auth import CurrentUser, require_admin

@pytest.mark.parametrize("role", ["student", "professor", "admin"])
def test_admin_guard(role):
    user = CurrentUser(id=uuid4(), role=role)
    if role == "admin":
        assert require_admin(user) == user
    else:
        with pytest.raises(HTTPException) as error:
            require_admin(user)
        assert error.value.status_code == 403
