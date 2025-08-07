# Legal Research Backend

A FastAPI-based backend application for tracking California legislative bills with AI-powered summaries and comprehensive admin management.

## Features

### 🏛️ **Bill Tracking & Management**
- Real-time California legislation tracking via OpenStates API
- AI-powered bill summarization using OpenAI
- Advanced search and filtering capabilities
- Bill caching for improved performance
- Detailed bill information and voting records

### 🔐 **Admin Dashboard**
- Secure JWT-based authentication
- Admin user management
- API key management for external services
- Cache management and database statistics
- Comprehensive admin controls

### 🔌 **API Integrations**
- **OpenStates API**: Legislative data retrieval
- **OpenAI**: AI-powered bill summarization
- **Google Civic API**: Representative information
- **SendGrid**: Email notification services

### 🗄️ **Database & CRUD Operations**
- SQLAlchemy ORM with SQLite database
- Async and sync CRUD operations
- Bill caching system
- Data persistence and migration support

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: SQLAlchemy with SQLite
- **Authentication**: JWT with python-jose
- **AI Integration**: OpenAI API
- **Server**: Uvicorn ASGI server
- **Testing**: Pytest with async support

## Project Structure

```
app/
├── api/                    # API route handlers
│   ├── admin.py           # Admin dashboard endpoints
│   ├── bills.py           # Bill tracking endpoints
│   ├── representatives.py # Representative data endpoints
│   └── widget.py          # Widget API endpoints
├── crud/                  # Database operations
│   ├── base.py            # Base CRUD operations
│   ├── bill_cache.py      # Bill caching operations
│   ├── bill_summary.py    # Bill summary operations
│   ├── bills.py           # Bill CRUD operations
│   └── representatives.py # Representative CRUD operations
├── models/                # Database models
│   ├── admin.py           # Admin user and API key models
│   ├── bills.py           # Bill and cache models
│   └── database.py        # Database configuration
├── services/              # External service integrations
│   ├── openai_service.py  # OpenAI integration
│   ├── openstates_api.py  # OpenStates API client
│   ├── google_civic_api.py # Google Civic API client
│   └── sendgrid_service.py # Email service
└── utils/                 # Utility functions
    └── text_extractor.py  # Text processing utilities
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/asaasinai/LegalResearch-backend.git
cd LegalResearch-backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory:
```env
# Database
DATABASE_URL=sqlite:///./redbird.db

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
OPENSTATES_API_KEY=your_openstates_api_key_here
GOOGLE_CIVIC_API_KEY=your_google_civic_api_key_here
SENDGRID_API_KEY=your_sendgrid_api_key_here

# JWT Configuration
SECRET_KEY=your_super_secret_jwt_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Initialize Database
```bash
python init_admin.py
```

### 6. Run the Application
```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the VS Code task
# Press Ctrl+Shift+P and run "Tasks: Run Task" -> "Start Backend"
```

## API Documentation

Once the server is running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Bills
- `GET /api/bills/` - Get bills with pagination and filtering
- `GET /api/bills/detail/{bill_id}` - Get detailed bill information
- `GET /api/bills/test` - Test endpoint for debugging

### Representatives
- `GET /api/representatives/` - Get representative information
- `GET /api/representatives/by-address` - Find representatives by address

### Admin
- `POST /api/admin/login` - Admin authentication
- `GET /api/admin/stats` - Dashboard statistics
- `POST /api/admin/clear-cache` - Cache management
- `GET /api/admin/summaries/search` - Search bill summaries
- `POST /api/admin/api-keys` - Manage API keys

### Widget
- `GET /api/widget/bills` - Widget-specific bill data

## Authentication

The admin dashboard uses JWT authentication:

1. **Login**: `POST /api/admin/login`
   ```json
   {
     "username": "admin",
     "password": "your_password"
   }
   ```

2. **Use Token**: Include in Authorization header:
   ```
   Authorization: Bearer your_jwt_token_here
   ```

## Development

### Running Tests
```bash
pytest
```

### Code Style
The project follows Python best practices:
- Type hints throughout the codebase
- Pydantic models for data validation
- Async/await for performance
- Comprehensive error handling

### Adding New Features
1. Add models in `app/models/`
2. Create CRUD operations in `app/crud/`
3. Add API endpoints in `app/api/`
4. Update database schema if needed

## Deployment

### Docker (Coming Soon)
```dockerfile
# Dockerfile will be added for containerized deployment
```

## License

This project is licensed under the Asaasin License - see the LICENSE file for details.


Built with ❤️ using FastAPI and modern Python tools.
