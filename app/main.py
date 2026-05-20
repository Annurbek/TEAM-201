from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.middleware.rbac import RBACMiddleware
from app.routers import router as api_router

app = FastAPI(title="Student Ranking System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add RBAC middleware
app.add_middleware(RBACMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "API is running"}
