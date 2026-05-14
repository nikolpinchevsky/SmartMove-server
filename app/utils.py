from datetime import datetime, timezone
import uuid
from ultralytics import YOLOWorld


model = None


AI_CLASSES = [
    # kitchen
    "plate", "plates", "bowl", "bowls", "cup", "cups", "glass", "glasses",
    "wine glass", "bottle", "fork", "knife", "spoon", "pan", "pot",
    "kettle", "toaster", "microwave", "oven",

    # clothes / bedroom
    "shirt", "t-shirt", "pants", "jeans", "shorts", "dress", "skirt",
    "jacket", "coat", "sweater", "hoodie", "socks", "underwear",
    "bra", "pajamas", "shoes", "sneakers", "hat", "cap", "scarf",
    "belt", "blanket", "pillow", "sheet", "towel",

    # electronics / office
    "laptop", "keyboard", "mouse", "cell phone", "phone", "tablet",
    "monitor", "charger", "cable", "headphones", "speaker", "remote",
    "camera", "book", "notebook", "paper", "pen", "pencil", "printer",

    # home
    "tv", "chair", "couch", "sofa", "lamp", "vase", "frame",
    "picture frame", "clock", "toy", "teddy bear", "backpack",
    "handbag", "suitcase", "bag", "box", "umbrella"
]


def get_model():
    global model
    if model is None:
        model = YOLOWorld("yolov8l-worldv2.pt")
        model.set_classes(AI_CLASSES)
    return model


def now_utc():
    return datetime.now(timezone.utc)


def generate_qr_identifier() -> str:
    return f"BOX-{uuid.uuid4().hex[:10].upper()}"


def analyze_box_image(image_path: str) -> dict:
    current_model = get_model()

    results = current_model.predict(
        image_path,
        conf=0.08,
        imgsz=960
    )

    detected = []

    for r in results:
        if r.boxes is not None:
            for c in r.boxes.cls:
                label = current_model.names[int(c)]
                detected.append(label)

    detected = sorted(list(set(detected)))

    room_rules = {
        "kitchen": [
            "plate", "plates", "bowl", "bowls", "cup", "cups", "glass", "glasses",
            "wine glass", "bottle", "fork", "knife", "spoon", "pan", "pot",
            "kettle", "toaster", "microwave", "oven"
        ],
        "bedroom": [
            "shirt", "t-shirt", "pants", "jeans", "shorts", "dress", "skirt",
            "jacket", "coat", "sweater", "hoodie", "socks", "underwear",
            "bra", "pajamas", "shoes", "sneakers", "hat", "cap", "scarf",
            "belt", "blanket", "pillow", "sheet", "towel", "suitcase"
        ],
        "office": [
            "laptop", "keyboard", "mouse", "cell phone", "phone", "tablet",
            "monitor", "charger", "cable", "headphones", "book", "notebook",
            "paper", "pen", "pencil", "printer", "camera"
        ],
        "living room": [
            "tv", "remote", "speaker", "chair", "couch", "sofa",
            "lamp", "vase", "frame", "picture frame", "clock"
        ],
        "bathroom": [
            "towel"
        ],
        "kids room": [
            "toy", "teddy bear"
        ],
        "storage": [
            "backpack", "handbag", "bag", "box", "umbrella"
        ]
    }

    fragile_objects = [
        "plate", "plates", "bowl", "bowls", "cup", "cups", "glass", "glasses",
        "wine glass", "bottle", "vase", "tv", "laptop", "cell phone",
        "phone", "tablet", "monitor", "camera", "lamp", "frame",
        "picture frame"
    ]

    valuable_objects = [
        "tv", "laptop", "cell phone", "phone", "tablet", "monitor",
        "keyboard", "mouse", "remote", "camera", "headphones",
        "speaker", "charger"
    ]

    suggested_fragile = any(obj in detected for obj in fragile_objects)
    suggested_valuable = any(obj in detected for obj in valuable_objects)

    destination_room = "general"
    box_name = "General Box"

    for room, objects in room_rules.items():
        if any(obj in detected for obj in objects):
            destination_room = room
            break

    if destination_room == "kitchen":
        box_name = "Kitchen Items"
    elif destination_room == "bedroom":
        box_name = "Bedroom Items"
    elif destination_room == "office":
        box_name = "Office Items"
    elif destination_room == "living room":
        box_name = "Living Room Items"
    elif destination_room == "bathroom":
        box_name = "Bathroom Items"
    elif destination_room == "kids room":
        box_name = "Kids Room Items"
    elif destination_room == "storage":
        box_name = "Storage Items"

    if suggested_fragile or suggested_valuable:
        priority_color = "red"
    elif detected:
        priority_color = "yellow"
    else:
        priority_color = "green"

    reason = f"Detected objects: {detected}" if detected else "No recognizable objects detected in the image."

    return {
        "box_name": box_name,
        "items": detected,
        "destination_room": destination_room,
        "priority_color": priority_color,
        "suggested_fragile": suggested_fragile,
        "suggested_valuable": suggested_valuable,
        "reason": reason
    }