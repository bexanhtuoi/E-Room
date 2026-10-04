from contextlib import asynccontextmanager

import models
from api import router
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.warm_all()
    yield


app = FastAPI(title="eroom-scorer", lifespan=lifespan)
app.include_router(router)
