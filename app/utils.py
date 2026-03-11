from datetime import datetime, timezone
import uuid
from ultralytics import YOLO


# load YOLO model once
model = YOLO("yolov8n.pt")

# Return current UTC datetime
# Used for created_at / updated_at fields 
def now_utc():
    return datetime.now(timezone.utc)

#  Generate unique identifier for box QR
def generate_qr_identifier() -> str:
    return f"BOX-{uuid.uuid4().hex[:10].upper()}"


# Analyze uploaded image 
def analyze_box_image(image_path: str) -> dict:
    """
    Analyze uploaded image using YOLO object detection.
    Returns auto-filled form suggestions.
    """

    results = model(image_path)

    detected = []

    for r in results:
        if r.boxes is not None:
            for c in r.boxes.cls:
                label = model.names[int(c)]
                detected.append(label)

    # Remove duplicates
    detected = list(set(detected))

    fragile_objects = ["cup", "wine glass", "bottle", "vase"]
    valuable_objects = ["tv", "laptop", "cell phone", "keyboard", "remote", "mouse"]

    suggested_fragile = any(obj in detected for obj in fragile_objects)
    suggested_valuable = any(obj in detected for obj in valuable_objects)

    # Suggested room
    if any(obj in detected for obj in ["cup", "bottle", "wine glass", "fork", "knife", "spoon"]):
        destination_room = "kitchen"
        box_name = "Kitchen Essentials"
    elif any(obj in detected for obj in ["tv", "remote", "chair"]):
        destination_room = "living room"
        box_name = "Living Room Items"
    elif any(obj in detected for obj in ["laptop", "keyboard", "mouse", "book"]):
        destination_room = "office"
        box_name = "Office Items"
    elif any(obj in detected for obj in ["bed", "clock"]):
        destination_room = "bedroom"
        box_name = "Bedroom Items"
    else:
        destination_room = "general"
        box_name = "General Box"

    # Suggested priority
    if suggested_fragile or suggested_valuable:
        priority_color = "red"
    elif detected:
        priority_color = "yellow"
    else:
        priority_color = "green"

    if detected:
        reason = f"Detected objects: {detected}"
    else:
        reason = "No recognizable objects detected in the image."

    return {
        "box_name": box_name,
        "items": detected,
        "destination_room": destination_room,
        "priority_color": priority_color,
        "suggested_fragile": suggested_fragile,
        "suggested_valuable": suggested_valuable,
        "reason": reason
    }