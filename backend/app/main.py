from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, detections, hazards, admin

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="API for crowd-sourced road hazard detection and alerting",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(
    detections.router, prefix=f"{settings.API_V1_PREFIX}/detections", tags=["Detections"]
)
app.include_router(hazards.router, prefix=f"{settings.API_V1_PREFIX}/hazards", tags=["Hazards"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Bump Aware API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get(f"{settings.API_V1_PREFIX}/stats")
async def get_statistics():
    """Get system statistics."""
    # TODO: Implement actual statistics from database
    return {
        "total_detections": 0,
        "total_hazards": 0,
        "active_hazards": 0,
        "total_users": 0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
    )
