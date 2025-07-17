# AI Mortgage Advisor Chatbot

A conversational AI chatbot that provides preliminary mortgage eligibility assessments through structured interviews with potential borrowers.

## Prerequisites
- Python 3.11+
- OpenAI API key
- Docker and Docker Compose

## Installation
```bash
# Install dependencies
pip install -e .

# Set environment variables
export OPENAI_API_KEY=your_api_key_here
export PYTHONPATH=$PWD
```

## Development Commands

### Quick Start
```bash
# Start both backend and frontend (recommended)
make run-all

# Stop both services when done
make stop-all
```

### Alternative: Run Services Separately
```bash
# Terminal 1 - Start the API Server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Start the Streamlit Web Interface
streamlit run streamlit_app.py
```

### Code Quality
```bash
# Format code and fix linting issues
make format

# Check linting without formatting
make lint

# Run all quality checks
make quality
```

### Testing
```bash
# Run tests
make test

# Run tests with coverage
make test-coverage
```

### Docker Operations
```bash
# Build and start services
docker-compose up --build

# Build Docker image only
make docker-build

# Run with Docker
make docker-run

# Stop Docker services
make docker-stop
```

## Access

Once running, the application will be available at:
- **🌐 Web Interface**: `http://localhost:8501` (Streamlit)
- **🔧 API Server**: `http://localhost:8000` (FastAPI)
- **📚 API Documentation**: `http://localhost:8000/docs`

## Project Structure

```
ai-mortgage-chatbot/
├── app/                    # Main application code
│   ├── models/            # Data models & database
│   ├── services/          # Business logic services
│   ├── utils/            # Logging & prompts
│   └── main.py           # FastAPI application
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── streamlit_app.py      # Frontend interface
├── docker-compose.yml    # Multi-service deployment
└── Makefile             # Development commands
```