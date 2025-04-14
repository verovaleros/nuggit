from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nuggit.api.routes import repositories
from nuggit.api.routes import detail

app = FastAPI(
    title="Nuggit API",
    description="API for managing and reviewing GitHub repositories",
    version="0.1.0"
)

# Optional: allow frontend apps to talk to API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
app.include_router(detail.router, prefix="/repositories", tags=["repository detail"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Nuggit API"}
