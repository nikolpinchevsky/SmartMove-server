# SmartMove Server

Backend API for **SmartMove** – a moving-box management system that helps users organize boxes during home relocation using projects, QR codes, box tracking, image upload, and AI-based image analysis.

The server is built with **FastAPI**, **MongoDB**, **JWT authentication**, and optional **YOLOv8 image analysis**.

## Main Features

- User registration and login
- JWT-based authentication
- Moving project creation and management
- Active project support
- Box creation and editing
- Automatic QR identifier generation for each box
- Box search and filtering
- Box status management
- Priority opening list
- Image upload for boxes
- AI image analysis using YOLOv8
- Apply AI suggestions to box details

## Technologies

- Python
- FastAPI
- Uvicorn
- MongoDB
- Motor
- JWT
- Passlib / bcrypt
- Python-dotenv
- Python-multipart
- Ultralytics YOLOv8
- OpenCV headless

## Requirements

Before running the server, install:

- Python 3.10 or newer
- MongoDB local database OR MongoDB Atlas account
- Git

## Installation

Clone the repository:

```bash
git clone https://github.com/nikolpinchevsky/SmartMove-server.git
cd SmartMove-server
```

## Create a virtual environment:
python -m venv venv

## Activate the virtual environment:

Windows:
venv\Scripts\activate

Mac / Linux:
source venv/bin/activate

Install dependencies:
pip install -r requirements.txt


## Environment Variables

Create a file named .env in the root folder of the project.

Example:
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=smartmove_db

JWT_SECRET_KEY=change_this_to_a_strong_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

For MongoDB Atlas, replace MONGO_URL with your connection string:
MONGO_URL=mongodb+srv://USERNAME:PASSWORD@cluster-url.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=smartmove_db

Important: Do not upload the real .env file to GitHub.


## Running the Server
Run the FastAPI server:

uvicorn app.main:app --reload

The server will run locally at:

http://127.0.0.1:8000

API documentation is available at:

http://127.0.0.1:8000/docs


## Connecting the Android App

If the Android app runs on an emulator, use:

http://10.0.2.2:8000

If the Android app runs on a real phone, use the computer's local IP address.

Example:

http://192.168.1.20:8000

In that case, run the server with:

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload


Checking the Server

After running the server, open:

http://127.0.0.1:8000/docs

If the Swagger page opens, the server is running correctly.

Important Notes

- Make sure the `.env` file is created before running the server.
- Do not upload the real `.env` file to GitHub.
- If using an Android emulator, the app should connect to `http://10.0.2.2:8000`.
- If using a real Android phone, the phone and computer must be on the same Wi-Fi network.
- .
