import fastapi
from starlette.middleware.cors import CORSMiddleware

from backend.app.auth.api import auth_router
from backend.app.db import database, metadata, engine
from backend.app.task.api import task_router

metadata.create_all(engine)

app = fastapi.FastAPI()
app.include_router(router=auth_router, prefix="/auth", tags=["auth"])
app.include_router(router=task_router, prefix="/task", tags=["task"])

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
