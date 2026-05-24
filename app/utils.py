from datetime import datetime, timezone
import uuid
from ultralytics import YOLOWorld


model = None


AI_CLASSES = [
    # kitchen
    "plate", "plates", "bowl", "bowls", "cup", "cups", "glass", "glasses",
    "mug", "mugs", "fork", "forks", "knife", "knives", "spoon", "spoons",
    "pot", "pots", "pan", "pans", "bottle", "bottles",
    "food container", "food containers", "kitchen towel", "kitchen towels",

    # bedroom / clothes
    "t-shirt", "t-shirts", "shirt", "shirts", "long sleeve shirt", "long sleeve shirts",
    "hoodie", "hoodies", "sweater", "sweaters", "jeans", "pants", "shorts",
    "dress", "dresses", "skirt", "skirts", "sock", "socks", "underwear",
    "bra", "bras", "pajamas", "jacket", "jackets", "coat", "coats",
    "shoe", "shoes", "sneaker", "sneakers", "belt", "belts", "hat", "hats",
    "blanket", "blankets", "pillow", "pillows", "bedsheet", "bedsheets",
    "towel", "towels",

    # bathroom
    "toothbrush", "toothbrushes", "toothpaste", "shampoo", "shampoos",
    "soap", "soaps", "hair dryer", "hair dryers", "toilet paper",

    # office / study
    "laptop", "laptops", "keyboard", "keyboards", "mouse", "mice",
    "charger", "chargers", "cable", "cables", "headphones",
    "book", "books", "notebook", "notebooks", "document", "documents",
    "folder", "folders",

    # living room / home
    "remote", "remotes", "speaker", "speakers", "lamp", "lamps",
    "picture frame", "picture frames", "candle", "candles",
    "vase", "vases", "decorations",

    # kids room
    "toy", "toys", "doll", "dolls", "teddy bear", "teddy bears",
    "lego", "legos",

    # storage / misc
    "backpack", "backpacks", "handbag", "handbags", "suitcase", "suitcases",
    "umbrella", "umbrellas", "bag", "bags"
]


LABEL_MAP = {
    "plate": "plates",
    "bowl": "bowls",
    "cup": "cups",
    "glass": "glasses",
    "mug": "mugs",
    "fork": "forks",
    "knife": "knives",
    "spoon": "spoons",
    "pot": "pots",
    "pan": "pans",
    "bottle": "bottles",
    "food container": "food containers",
    "kitchen towel": "kitchen towels",

    "t-shirt": "t-shirts",
    "shirt": "shirts",
    "long sleeve shirt": "long sleeve shirts",
    "hoodie": "hoodies",
    "sweater": "sweaters",
    "dress": "dresses",
    "skirt": "skirts",
    "sock": "socks",
    "bra": "bras",
    "jacket": "jackets",
    "coat": "coats",
    "shoe": "shoes",
    "sneaker": "sneakers",
    "belt": "belts",
    "hat": "hats",
    "blanket": "blankets",
    "pillow": "pillows",
    "bedsheet": "bedsheets",
    "towel": "towels",

    "toothbrush": "toothbrushes",
    "shampoo": "shampoos",
    "soap": "soaps",
    "hair dryer": "hair dryers",

    "laptop": "laptops",
    "keyboard": "keyboards",
    "mouse": "mice",
    "charger": "chargers",
    "cable": "cables",
    "book": "books",
    "notebook": "notebooks",
    "document": "documents",
    "folder": "folders",

    "remote": "remotes",
    "speaker": "speakers",
    "lamp": "lamps",
    "picture frame": "picture frames",
    "candle": "candles",
    "vase": "vases",

    "toy": "toys",
    "doll": "dolls",
    "teddy bear": "teddy bears",
    "lego": "legos",

    "backpack": "backpacks",
    "handbag": "handbags",
    "suitcase": "suitcases",
    "umbrella": "umbrellas",
    "bag": "bags"
}


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
        conf=0.25,
        imgsz=960
    )

    detected = []

    for r in results:
        if r.boxes is not None:
            for c in r.boxes.cls:
                label = current_model.names[int(c)]
                label = LABEL_MAP.get(label, label)
                detected.append(label)

    detected = sorted(list(set(detected)))

    room_rules = {
        "kitchen": [
            "plates", "bowls", "cups", "glasses", "mugs",
            "forks", "knives", "spoons",
            "pots", "pans", "bottles",
            "food containers", "kitchen towels"
        ],

        "bedroom": [
            "t-shirts", "shirts", "long sleeve shirts",
            "hoodies", "sweaters", "jeans", "pants", "shorts",
            "dresses", "skirts", "socks", "underwear", "bras",
            "pajamas", "jackets", "coats", "shoes", "sneakers",
            "belts", "hats", "blankets", "pillows", "bedsheets"
        ],

        "bathroom": [
            "toothbrushes", "toothpaste", "shampoos", "soaps",
            "hair dryers", "toilet paper", "towels"
        ],

        "office": [
            "laptops", "keyboards", "mice", "chargers", "cables",
            "headphones", "books", "notebooks", "documents", "folders"
        ],

        "living room": [
            "remotes", "speakers", "lamps", "picture frames",
            "candles", "vases", "decorations"
        ],

        "kids room": [
            "toys", "dolls", "teddy bears", "legos"
        ],

        "storage": [
            "backpacks", "handbags", "suitcases", "umbrellas", "bags"
        ]
    }

    fragile_objects = [
        "plates", "bowls", "cups", "glasses", "mugs",
        "bottles", "lamps", "picture frames", "candles",
        "vases", "laptops", "keyboards", "mice",
        "speakers", "headphones", "chargers", "hair dryers"
    ]

    valuable_objects = [
        "laptops", "keyboards", "mice", "chargers",
        "headphones", "speakers", "hair dryers",
        "handbags", "suitcases", "books", "notebooks",
        "documents", "folders"
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