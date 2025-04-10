# Emotion Detection Backend

Backend service for facial emotion recognition using deep learning.

## Features

- Real-time emotion detection from webcam
- Image processing and analysis
- RESTful API endpoints
- SQLite database for storing results
- JWT authentication
- CORS support

## Requirements

- Python 3.8+
- Flask
- OpenCV
- TensorFlow
- SQLAlchemy
- Other dependencies listed in requirements.txt

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
- Copy `.env.example` to `.env`
- Update variables as needed

4. Initialize database:
```bash
python init_db.py
```

## Running the Server

Development mode:
```bash
flask run
```

Production mode:
```bash
python app.py
```

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - User login
- POST `/api/auth/refresh` - Refresh access token

### Emotion Detection
- POST `/api/detect-emotion` - Detect emotion from image
- GET `/api/emotions` - Get emotion history
- GET `/api/image/<id>` - Get original image
- GET `/api/processed-image/<id>` - Get processed image

## Directory Structure

```
backend/
├── app.py              # Main application file
├── models.py           # Database models
├── init_db.py          # Database initialization
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
└── camera*/           # Image storage directories
```

## Error Handling

The application includes comprehensive error handling for:
- Database operations
- Image processing
- Authentication
- API requests

## Security

- JWT-based authentication
- Password hashing
- CORS protection
- Environment variable configuration

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request 