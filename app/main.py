import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.middleware.rate_limiter import apply_rate_limiting
from app.models.database import create_database_engine, create_tables, get_session_maker
from app.models.mortgage import ChatRequest, ChatResponse, HealthResponse
from app.services.database_service import DatabaseService
from app.services.persistent_conversation_service import PersistentConversationService
from app.utils.logger import configure_logging, get_logger, log_api_request

# Configure structured logging
configure_logging(log_level=settings.log_level, log_format=settings.log_format)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A conversational AI chatbot for preliminary mortgage eligibility assessment",
    version=settings.app_version,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply rate limiting
limiter = apply_rate_limiting(app)

# Database setup
engine = create_database_engine()
SessionLocal = get_session_maker(engine)


def get_database_session() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_conversation_service(
    db: Session = Depends(get_database_session),
) -> PersistentConversationService:
    """Dependency to get conversation service instance"""
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key is not configured. Please set OPENAI_API_KEY environment variable.",
        )
    # Create new service instance for each request with fresh DB session
    db_service = DatabaseService(db)
    return PersistentConversationService(settings.openai_api_key, db_service)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(
        "Application starting", app_name=settings.app_name, debug=settings.debug
    )

    # Create database tables
    try:
        create_tables(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise

    if not settings.openai_api_key:
        logger.warning(
            "OpenAI API key not configured",
            help="Please set OPENAI_API_KEY environment variable",
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok")


if limiter:

    @app.post("/chat", response_model=ChatResponse)
    @limiter.limit(f"{settings.max_requests_per_minute}/minute")
    async def chat(
        request: Request,
        chat_request: ChatRequest,
        conversation_service: PersistentConversationService = Depends(
            get_conversation_service
        ),
    ):
        """
        Chat endpoint for processing user messages and returning bot responses.

        This endpoint handles the conversational flow for mortgage eligibility assessment.
        It maintains conversation state and returns appropriate responses based on the
        current step in the data collection process.

        Rate limited to prevent abuse.
        """
        start_time = time.time()
        api_logger = log_api_request(
            method="POST",
            path="/chat",
            user_agent=request.headers.get("user-agent", ""),
            content_length=len(chat_request.message),
        )

        try:
            api_logger.info(
                "Processing chat request", message_preview=chat_request.message[:50]
            )

            # Process the user message
            response = conversation_service.process_message(
                user_message=chat_request.message,
                conversation_id=chat_request.conversation_id,
            )

            duration_ms = (time.time() - start_time) * 1000
            api_logger.info(
                "Chat request processed successfully",
                duration_ms=duration_ms,
                response_length=len(response["response"]),
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            api_logger.error(
                "Error processing chat request",
                error=str(e),
                duration_ms=duration_ms,
                status_code=500,
            )
            raise HTTPException(
                status_code=500, detail=f"Error processing your request: {str(e)}"
            ) from e

else:

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        request: Request,
        chat_request: ChatRequest,
        conversation_service: PersistentConversationService = Depends(
            get_conversation_service
        ),
    ):
        """
        Chat endpoint for processing user messages and returning bot responses.

        This endpoint handles the conversational flow for mortgage eligibility assessment.
        It maintains conversation state and returns appropriate responses based on the
        current step in the data collection process.

        Rate limited to prevent abuse.
        """
        start_time = time.time()
        api_logger = log_api_request(
            method="POST",
            path="/chat",
            user_agent=request.headers.get("user-agent", ""),
            content_length=len(chat_request.message),
        )

        try:
            api_logger.info(
                "Processing chat request", message_preview=chat_request.message[:50]
            )

            # Process the user message
            response = conversation_service.process_message(
                user_message=chat_request.message,
                conversation_id=chat_request.conversation_id,
            )

            duration_ms = (time.time() - start_time) * 1000
            api_logger.info(
                "Chat request processed successfully",
                duration_ms=duration_ms,
                response_length=len(response["response"]),
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            api_logger.error(
                "Error processing chat request",
                error=str(e),
                duration_ms=duration_ms,
                status_code=500,
            )
            raise HTTPException(
                status_code=500, detail=f"Error processing your request: {str(e)}"
            ) from e


@app.post("/conversation/reset")
async def reset_conversation(
    request: Request,
    conversation_service: PersistentConversationService = Depends(
        get_conversation_service
    ),
):
    """
    Reset conversation state (useful for testing).
    This endpoint is not required by the spec but useful for development.
    """
    api_logger = log_api_request(
        method="POST",
        path="/conversation/reset",
        user_agent=request.headers.get("user-agent", ""),
    )

    try:
        api_logger.info("Starting new conversation")
        conversation_id = conversation_service.start_new_conversation()
        api_logger.info(
            "New conversation started successfully", conversation_id=conversation_id
        )
        return {
            "message": "New conversation started successfully",
            "conversation_id": conversation_id,
        }
    except Exception as e:
        api_logger.error("Error resetting conversation", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Error resetting conversation: {str(e)}"
        ) from e


@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "Welcome to the AI Mortgage Advisor Chatbot API",
        "endpoints": {"chat": "/chat", "health": "/health", "docs": "/docs"},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
