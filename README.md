# SmartMove Server 🚚

Backend API for the SmartMove mobile application.

The server manages users, projects, rooms, and moving boxes, while providing secure authentication, QR-based box identification, and AI-powered image analysis.

## Features

- User registration and login
- JWT authentication and authorization
- Project management
- Room management
- Box management
- QR identifier generation and lookup
- Search and filtering
- Priority opening list
- AI image analysis using YOLOWorld
- MongoDB data storage

## Tech Stack

- FastAPI
- MongoDB
- Motor (Async MongoDB Driver)
- JWT Authentication
- Passlib (Password Hashing)
- YOLOWorld AI Model
- Python

## API Documentation

After running the server locally:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Mobile Application

Android application repository:

🔗 https://github.com/nikolpinchevsky/SmartMove

## Authors

- Nikol Pinchevsky
- May Shabat
