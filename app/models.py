from pydantic import BaseModel, EmailStr, Field
from enum import Enum


#  Allowed priority colors for a box
class PriorityColor(str, Enum):
    red = "red"
    yellow = "yellow"
    green = "green"


# Allowed box statuses in the moving process
class BoxStatus(str, Enum):
    closed = "closed"
    opened = "opened"
    packed = "packed"
    moved = "moved"
    unpacked = "unpacked"


# ---------- Auth Models ----------
# Request body for user registration
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

# Request body for user login
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

# Response returned after register/login
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Project Models ----------
# Request body for creating a new project
class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)

#  Request body for updating project fields
# All fields are optional in PATCH
class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None


# ---------- Box Models ----------
# Request body for creating a new box
class BoxCreateRequest(BaseModel):
    project_id: str
    name: str = Field(..., min_length=1, max_length=150)
    fragile: bool = False
    valuable: bool = False
    priority_color: PriorityColor
    destination_room: str = Field(..., min_length=1, max_length=100)
    items: list[str] = Field(default_factory=list)
    status: BoxStatus = BoxStatus.closed

# Request body for updating a box.
class BoxUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    fragile: bool | None = None
    valuable: bool | None = None
    priority_color: PriorityColor | None = None
    destination_room: str | None = Field(default=None, min_length=1, max_length=100)
    items: list[str] | None = None
    status: BoxStatus | None = None

# Request body for updating only box status
class BoxStatusUpdateRequest(BaseModel):
    status: BoxStatus


    