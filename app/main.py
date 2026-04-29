from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from bson import ObjectId
from bson.errors import InvalidId
import os
import shutil
import uuid

from app.db import users_collection, projects_collection, boxes_collection, rooms_collection
from app.models import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    BoxCreateRequest,
    BoxUpdateRequest,
    BoxStatusUpdateRequest,
    RoomCreateRequest
)
from app.auth import hash_password, verify_password, create_access_token
from app.deps import get_current_user
from app.utils import now_utc, analyze_box_image

app = FastAPI(title="SmartMove API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ---------- MongoDB Indexes ----------
# Run once when the server starts
@app.on_event("startup")
async def startup_indexes():
    await boxes_collection.create_index("qr_identifier", unique=True)
    await boxes_collection.create_index(
        [("project_id", 1), ("box_number", 1)],
        unique=True
    )
    await rooms_collection.create_index(
        [("user_id", 1), ("project_id", 1), ("name_lower", 1)],
        unique=True
    )

    
def parse_object_id(id_value: str) -> ObjectId:
    """
    Safely convert string ID into MongoDB ObjectId.
    If the ID format is invalid, return HTTP 400 instead of server crash.
    """
    try:
        return ObjectId(id_value)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")


# ---------- Register ----------
@app.post("/auth/register", response_model=TokenResponse)
async def register_user(payload: UserRegisterRequest):
    """
    Create a new user account.

    Steps:
    1. Check if email already exists
    2. Hash the password
    3. Save the user in MongoDB
    4. Create JWT token
    5. Return the token
    """

    # Check if a user with this email already exists
    existing_user = await users_collection.find_one({"email": payload.email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Prepare new user document for MongoDB
    new_user = {
        "name": payload.name,
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "created_at": now_utc(),
        "updated_at": now_utc()
    }

    # Insert new user into database
    result = await users_collection.insert_one(new_user)

    # Create access token for the new user
    access_token = create_access_token({
        "user_id": str(result.inserted_id),
        "email": payload.email.lower()
    })

    # Return token to client
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ---------- Login ----------
@app.post("/auth/login", response_model=TokenResponse)
async def login_user(payload: UserLoginRequest):
    """
    Authenticate existing user.

    Steps:
    1. Find user by email
    2. Verify password
    3. Create JWT token
    4. Return the token
    """

    # Find user by email
    user = await users_collection.find_one({"email": payload.email.lower()})

    # If user does not exist or password is wrong, return 401
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create access token
    access_token = create_access_token({
        "user_id": str(user["_id"]),
        "email": user["email"]
    })

    # Return token to client
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/auth/me")
async def get_current_user_profile(current_user=Depends(get_current_user)):
    """
    Return the profile of the currently authenticated user.
    """

    # Find user by ID from JWT token
    user = await users_collection.find_one({"_id": parse_object_id(current_user["user_id"])})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return safe public user data
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"]
    }


# ---------- Create Project ----------
@app.post("/projects")
async def create_project(payload: ProjectCreateRequest, current_user=Depends(get_current_user)):
    """
    Create a new moving project for the logged-in user.

    Business rule:
    Only one project can be active at a time.
    So before creating a new active project,
    we set all previous projects to is_active = False.
    """

    # Set all existing projects of this user to inactive
    await projects_collection.update_many(
        {"user_id": current_user["user_id"]},
        {"$set": {"is_active": False, "updated_at": now_utc()}}
    )

    # Prepare new project document
    new_project = {
        "user_id": current_user["user_id"],
        "name": payload.name,
        "is_active": True,
        "created_at": now_utc(),
        "updated_at": now_utc()
    }

    # Insert project into database
    result = await projects_collection.insert_one(new_project)

    # Create default rooms for this project
    default_rooms = ["Kitchen", "Living Room", "Bedroom", "Bathroom", "Office"]

    await rooms_collection.insert_many([
        {
            "user_id": current_user["user_id"],
            "project_id": str(result.inserted_id),
            "name": room,
            "name_lower": room.lower(),
            "created_at": now_utc(),
            "updated_at": now_utc()
        }
        for room in default_rooms
    ])

    # Return created project info
    return {
        "id": str(result.inserted_id),
        "name": payload.name,
        "is_active": True
    }


@app.get("/projects")
async def list_projects(current_user=Depends(get_current_user)):
    """
    Return all projects of the current user.
    Newest projects appear first.
    """

    cursor = projects_collection.find(
        {"user_id": current_user["user_id"]}
    ).sort("created_at", -1)

    projects = []

    async for project in cursor:
        projects.append({
            "id": str(project["_id"]),
            "name": project["name"],
            "is_active": project.get("is_active", False),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at")
        })

    return {"projects": projects}


# ---------- Get Project Details ----------
@app.get("/projects/active")
async def get_active_project(current_user=Depends(get_current_user)):
    """
    Return the currently active project of the logged-in user.
    """

    project = await projects_collection.find_one({
        "user_id": current_user["user_id"],
        "is_active": True
    })

    if not project:
        return {"project": None}

    return {
        "project": {
            "id": str(project["_id"]),
            "name": project["name"],
            "is_active": project["is_active"],
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at")
        }
    }


@app.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    current_user=Depends(get_current_user)
):
    """
    Update project fields such as name or active status.
    Only the owner of the project can update it.
    """

    project_object_id = parse_object_id(project_id)

    # Check that project exists and belongs to current user
    project = await projects_collection.find_one({
        "_id": project_object_id,
        "user_id": current_user["user_id"]
    })

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updates = {}

    # Update project name if provided
    if payload.name is not None:
        updates["name"] = payload.name

    # Update active flag if provided
    if payload.is_active is not None:
        if payload.is_active:
            # Only one active project per user
            await projects_collection.update_many(
                {"user_id": current_user["user_id"]},
                {"$set": {"is_active": False, "updated_at": now_utc()}}
            )
            updates["is_active"] = True
        else:
            updates["is_active"] = False

    # Apply updates if there is anything to update
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = now_utc()

    await projects_collection.update_one(
        {"_id": project_object_id},
        {"$set": updates}
    )

    updated_project = await projects_collection.find_one({"_id": project_object_id})

    return {
        "id": str(updated_project["_id"]),
        "name": updated_project["name"],
        "is_active": updated_project["is_active"],
        "created_at": updated_project.get("created_at"),
        "updated_at": updated_project.get("updated_at")
    }

# ---------- Rooms ----------
@app.post("/rooms")
async def create_room(payload: RoomCreateRequest, current_user=Depends(get_current_user)):
    project_object_id = parse_object_id(payload.project_id)

    project = await projects_collection.find_one({
        "_id": project_object_id,
        "user_id": current_user["user_id"]
    })

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    room_name = payload.name.strip()

    if not room_name:
        raise HTTPException(status_code=400, detail="Room name cannot be empty")

    existing_room = await rooms_collection.find_one({
        "user_id": current_user["user_id"],
        "project_id": payload.project_id,
        "name_lower": room_name.lower()
    })

    if existing_room:
        raise HTTPException(status_code=400, detail="Room already exists")

    new_room = {
        "user_id": current_user["user_id"],
        "project_id": payload.project_id,
        "name": room_name,
        "name_lower": room_name.lower(),
        "created_at": now_utc(),
        "updated_at": now_utc()
    }

    result = await rooms_collection.insert_one(new_room)

    return {
        "id": str(result.inserted_id),
        "project_id": payload.project_id,
        "name": room_name
    }


@app.get("/rooms")
async def list_rooms(
    project_id: str | None = Query(default=None),
    current_user=Depends(get_current_user)
):
    query = {"user_id": current_user["user_id"]}

    if project_id:
        query["project_id"] = project_id
    else:
        active_project = await projects_collection.find_one({
            "user_id": current_user["user_id"],
            "is_active": True
        })

        if not active_project:
            return {"rooms": []}

        query["project_id"] = str(active_project["_id"])

    cursor = rooms_collection.find(query).sort("name", 1)

    rooms = []

    async for room in cursor:
        rooms.append({
            "id": str(room["_id"]),
            "project_id": room["project_id"],
            "name": room["name"],
            "created_at": room.get("created_at"),
            "updated_at": room.get("updated_at")
        })

    return {"rooms": rooms}

# ---------- Create Box ----------
@app.post("/boxes")
async def create_box(payload: BoxCreateRequest, current_user=Depends(get_current_user)):
    """
    Create a new box inside a specific project.

    Steps:
    1. Verify that the project exists and belongs to the current user
    2. Generate the next box_number inside this project
    3. Generate unique QR identifier
    4. Insert box into MongoDB
    5. Return created box data
    """

    project_object_id = parse_object_id(payload.project_id)

    # Verify that the project exists and belongs to the logged-in user
    project = await projects_collection.find_one({
        "_id": project_object_id,
        "user_id": current_user["user_id"]
    })

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find last box number in this project
    last_box = await boxes_collection.find_one(
        {"project_id": payload.project_id, "user_id": current_user["user_id"]},
        sort=[("box_number", -1)]
    )

    next_box_number = 1
    if last_box and "box_number" in last_box:
        next_box_number = last_box["box_number"] + 1

    # Generate unique QR code identifier for this box
    qr_identifier = f"SM-{payload.project_id}-{next_box_number}-{uuid.uuid4().hex[:8]}"

    # Prepare new box document
    new_box = {
        "user_id": current_user["user_id"],
        "project_id": payload.project_id,
        "box_number": next_box_number,
        "name": payload.name,
        "fragile": payload.fragile,
        "valuable": payload.valuable,
        "priority_color": payload.priority_color.value,
        "destination_room": payload.destination_room,
        "items": payload.items,
        "status": payload.status.value,
        "qr_identifier": qr_identifier,
        "image_url": None,
        "ai_metadata": None,
        "created_at": now_utc(),
        "updated_at": now_utc()
    }

    # Insert box into database
    result = await boxes_collection.insert_one(new_box)

    # Return created box info
    return {
        "id": str(result.inserted_id),
        "project_id": payload.project_id,
        "box_number": next_box_number,
        "name": payload.name,
        "fragile": payload.fragile,
        "valuable": payload.valuable,
        "priority_color": payload.priority_color.value,
        "destination_room": payload.destination_room,
        "items": payload.items,
        "status": payload.status.value,
        "qr_identifier": qr_identifier,
        "image_url": None
    }


@app.get("/boxes")
async def list_boxes(
    project_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    room: str | None = Query(default=None),
    priority_color: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user=Depends(get_current_user)
):
    """
    Return boxes of the current user.
    Supports optional filtering by:
    - project_id
    - search text
    - room
    - priority color
    - status
    """

    query = {"user_id": current_user["user_id"]}

    # If project_id is not provided, use the active project if it exists
    if project_id:
        query["project_id"] = project_id
    else:
        active_project = await projects_collection.find_one({
            "user_id": current_user["user_id"],
            "is_active": True
        })
        if active_project:
            query["project_id"] = str(active_project["_id"])

    # Filter by destination room
    if room:
        query["destination_room"] = {"$regex": room, "$options": "i"}

    # Filter by priority color
    if priority_color:
        query["priority_color"] = priority_color

    # Filter by status
    if status:
        query["status"] = status

    # General search across name, items, room and QR identifier
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"items": {"$elemMatch": {"$regex": q, "$options": "i"}}},
            {"destination_room": {"$regex": q, "$options": "i"}},
            {"qr_identifier": {"$regex": q, "$options": "i"}}
        ]

    cursor = boxes_collection.find(query).sort("created_at", -1)

    boxes = []

    async for box in cursor:
        boxes.append({
            "id": str(box["_id"]),
            "project_id": box["project_id"],
            "box_number": box.get("box_number"),
            "name": box["name"],
            "fragile": box["fragile"],
            "valuable": box["valuable"],
            "priority_color": box["priority_color"],
            "destination_room": box["destination_room"],
            "items": box.get("items", []),
            "status": box["status"],
            "qr_identifier": box["qr_identifier"],
            "image_url": box.get("image_url"),
            "ai_metadata": box.get("ai_metadata"),
            "created_at": box.get("created_at"),
            "updated_at": box.get("updated_at")
        })

    return {"boxes": boxes}


# ---------- Get Box Details ----------
# Return one box by its database ID.
# Only the owner can access it.
@app.get("/boxes/{box_id}")
async def get_box_by_id(box_id: str, current_user=Depends(get_current_user)):

    box = await boxes_collection.find_one({
        "_id": parse_object_id(box_id),
        "user_id": current_user["user_id"]
    })

    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    return {
        "id": str(box["_id"]),
        "project_id": box["project_id"],
        "box_number": box.get("box_number"),
        "name": box["name"],
        "fragile": box["fragile"],
        "valuable": box["valuable"],
        "priority_color": box["priority_color"],
        "destination_room": box["destination_room"],
        "items": box.get("items", []),
        "status": box["status"],
        "qr_identifier": box["qr_identifier"],
        "image_url": box.get("image_url"),
        "ai_metadata": box.get("ai_metadata"),
        "created_at": box.get("created_at"),
        "updated_at": box.get("updated_at")
    }


# ---------- Get Box by QR ----------
@app.get("/boxes/by-qr/{qr_identifier}")
async def get_box_by_qr(qr_identifier: str, current_user=Depends(get_current_user)):
    """
    Return a box using its QR identifier.
    This endpoint is useful for QR scanning in the mobile app.
    """

    box = await boxes_collection.find_one({
        "qr_identifier": qr_identifier,
        "user_id": current_user["user_id"]
    })

    if not box:
        raise HTTPException(status_code=404, detail="Box not found for this QR")

    return {
        "id": str(box["_id"]),
        "project_id": box["project_id"],
        "box_number": box.get("box_number"),
        "name": box["name"],
        "fragile": box["fragile"],
        "valuable": box["valuable"],
        "priority_color": box["priority_color"],
        "destination_room": box["destination_room"],
        "items": box.get("items", []),
        "status": box["status"],
        "qr_identifier": box["qr_identifier"],
        "image_url": box.get("image_url"),
        "ai_metadata": box.get("ai_metadata"),
        "created_at": box.get("created_at"),
        "updated_at": box.get("updated_at")
    }


#----------- GET boxes priority opening list -----------
@app.get("/boxes/priority/open-first")
async def get_priority_opening_list(
    project_id: str | None = Query(default=None),
    current_user=Depends(get_current_user)
):
    """
    Return boxes that should be opened first.
    Business rule used here:
    - priority_color must be red
    - status must still be closed
    """

    # If project_id is missing, use active project
    if not project_id:
        active_project = await projects_collection.find_one({
            "user_id": current_user["user_id"],
            "is_active": True
        })

        if not active_project:
            return {"boxes": []}

        project_id = str(active_project["_id"])

    cursor = boxes_collection.find({
        "user_id": current_user["user_id"],
        "project_id": project_id,
        "priority_color": "red",
        "status": "closed"
    }).sort("created_at", 1)

    boxes = []

    async for box in cursor:
        boxes.append({
            "id": str(box["_id"]),
            "box_number": box.get("box_number"),
            "name": box["name"],
            "destination_room": box["destination_room"],
            "priority_color": box["priority_color"],
            "status": box["status"],
            "qr_identifier": box["qr_identifier"],
            "image_url": box.get("image_url"),
            "created_at": box.get("created_at"),
            "updated_at": box.get("updated_at")
        })

    return {"boxes": boxes}


#---------- Update Box ----------
@app.patch("/boxes/{box_id}")
async def update_box(
    box_id: str,
    payload: BoxUpdateRequest,
    current_user=Depends(get_current_user)
):
    """
    Update box fields such as name, room, priority, items or status.
    Only the owner of the box can update it.
    """

    box_object_id = parse_object_id(box_id)

    # Check that box exists and belongs to current user
    box = await boxes_collection.find_one({
        "_id": box_object_id,
        "user_id": current_user["user_id"]
    })

    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    updates = {}
    data = payload.model_dump(exclude_none=True)

    # Convert enum values to plain strings before saving to MongoDB
    for key, value in data.items():
        if hasattr(value, "value"):
            updates[key] = value.value
        else:
            updates[key] = value

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = now_utc()

    await boxes_collection.update_one(
        {"_id": box_object_id},
        {"$set": updates}
    )

    updated_box = await boxes_collection.find_one({"_id": box_object_id})

    return {
        "id": str(updated_box["_id"]),
        "project_id": updated_box["project_id"],
        "box_number": updated_box.get("box_number"),
        "name": updated_box["name"],
        "fragile": updated_box["fragile"],
        "valuable": updated_box["valuable"],
        "priority_color": updated_box["priority_color"],
        "destination_room": updated_box["destination_room"],
        "items": updated_box.get("items", []),
        "status": updated_box["status"],
        "qr_identifier": updated_box["qr_identifier"],
        "image_url": updated_box.get("image_url"),
        "ai_metadata": updated_box.get("ai_metadata"),
        "created_at": updated_box.get("created_at"),
        "updated_at": updated_box.get("updated_at")
    }


#---------- Update Box Status ----------
@app.patch("/boxes/{box_id}/status")
async def update_box_status(
    box_id: str,
    payload: BoxStatusUpdateRequest,
    current_user=Depends(get_current_user)
):
    """
    Update only the status of a box.
    This is useful for quick actions in the mobile app.
    """

    box_object_id = parse_object_id(box_id)

    # Check that the box exists and belongs to current user
    box = await boxes_collection.find_one({
        "_id": box_object_id,
        "user_id": current_user["user_id"]
    })

    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    # Update status field only
    await boxes_collection.update_one(
        {"_id": box_object_id},
        {
            "$set": {
                "status": payload.status.value,
                "updated_at": now_utc()
            }
        }
    )

    return {
        "ok": True,
        "status": payload.status.value
    }


# ---------- Upload Box Image ----------
# Upload image for a specific box
# Save the file locally and store image URL in MongoDB
@app.post("/boxes/{box_id}/upload-image")
async def upload_box_image(
    box_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):

    box_object_id = parse_object_id(box_id)

    # Check that the box exists and belongs to current user
    box = await boxes_collection.find_one({
        "_id": box_object_id,
        "user_id": current_user["user_id"]
    })

    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, and PNG image files are allowed"
    )

    # Create unique file name
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    safe_file_name = f"{box_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_file_name)

    # Save file to uploads directory
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/uploads/{safe_file_name}"

    # Save image path in box document
    await boxes_collection.update_one(
        {"_id": box_object_id},
        {
            "$set": {
                "image_url": image_url,
                "updated_at": now_utc()
            }
        }
    )

    return {
        "ok": True,
        "image_url": image_url,
        "file_name": safe_file_name
    }


# ---------- Analyze Image For New Box Form ----------
@app.post("/ai/analyze-box-image")
async def analyze_box_image_for_form(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """
    Analyze an uploaded image before creating a box.
    Returns form suggestions only, without requiring box_id
    and without creating/saving a box yet.
    """

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, and PNG image files are allowed"
        )

    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    temp_file_name = f"temp_{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, temp_file_name)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = analyze_box_image(file_path)

        if not result["items"]:
            return {
                "ok": False,
                "message": "AI could not recognize objects in this image. Please fill the form manually.",
                "form_suggestions": None,
                "ai_metadata": {
                    "detected_categories": [],
                    "reason": result.get("reason", "No recognizable objects detected."),
                    "approved": False,
                    "saved_at": now_utc()
                }
            }

        ai_metadata = {
            "detected_categories": result["items"],
            "suggested_fragile": result["suggested_fragile"],
            "suggested_valuable": result["suggested_valuable"],
            "suggested_priority_color": result["priority_color"],
            "suggested_destination_room": result["destination_room"],
            "suggested_box_name": result["box_name"],
            "reason": result.get("reason", ""),
            "approved": False,
            "saved_at": now_utc()
        }

        return {
            "ok": True,
            "message": "AI analysis completed successfully.",
            "form_suggestions": {
                "name": result["box_name"],
                "items": result["items"],
                "destination_room": result["destination_room"],
                "priority_color": result["priority_color"],
                "fragile": result["suggested_fragile"],
                "valuable": result["suggested_valuable"]
            },
            "ai_metadata": ai_metadata
        }

    except Exception:
        return {
            "ok": False,
            "message": "AI analysis failed. Please fill the form manually.",
            "form_suggestions": None,
            "ai_metadata": None
        }

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)