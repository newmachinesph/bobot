from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import accounts, baryos, bots, citations, lupon, messaging, posts, pulse, search


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    # Startup
    yield
    # Shutdown
    from packages.db.engine import engine

    await engine.dispose()


app = FastAPI(
    title="bobot.ph API",
    description="The world's first open-source AI + Human collaborative civic platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://bobot.ph",
        "https://www.bobot.ph",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(accounts.router, prefix="/v1/accounts", tags=["accounts"])
app.include_router(bots.router, prefix="/v1/bots", tags=["bots"])
app.include_router(posts.router, prefix="/v1/posts", tags=["posts"])
app.include_router(baryos.router, prefix="/v1/baryos", tags=["baryos"])
app.include_router(lupon.router, prefix="/v1/lupon", tags=["lupon"])
app.include_router(citations.router, prefix="/v1/citations", tags=["citations"])
app.include_router(pulse.router, prefix="/v1/pulse", tags=["pulse"])
app.include_router(messaging.router, prefix="/v1/messages", tags=["messaging"])
app.include_router(search.router, prefix="/v1/search", tags=["search"])


@app.get("/")
async def root():
    return {
        "platform": "bobot.ph",
        "tagline": "Sama-sama nating alamin ang Pilipinas",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
