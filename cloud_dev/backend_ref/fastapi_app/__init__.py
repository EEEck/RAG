import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict, Union

import fastapi
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fastapi_app.dependencies import (
    FastAPIAppContext,
    common_parameters,
    create_async_sessionmaker,
)
from fastapi_app.openai_clients import create_openai_chat_client, create_openai_embed_client
from fastapi_app.postgres_engine import create_postgres_engine_from_env

logger = logging.getLogger("ragapp")


class State(TypedDict):
    sessionmaker: async_sessionmaker[AsyncSession]
    context: FastAPIAppContext
    chat_client: Union[AsyncOpenAI, AsyncAzureOpenAI]
    embed_client: Union[AsyncOpenAI, AsyncAzureOpenAI]


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> AsyncIterator[State]:
    context = await common_parameters()

    engine = await create_postgres_engine_from_env()
    sessionmaker = await create_async_sessionmaker(engine)
    chat_client = await create_openai_chat_client()
    embed_client = await create_openai_embed_client()

    yield {"sessionmaker": sessionmaker, "context": context, "chat_client": chat_client, "embed_client": embed_client}
    await engine.dispose()


def create_app(testing: bool = False):
    if os.getenv("RUNNING_IN_PRODUCTION"):
        logging.basicConfig(level=logging.INFO)
    else:
        if not testing:
            load_dotenv(override=True)
        logging.basicConfig(level=logging.INFO)

    app = fastapi.FastAPI(docs_url="/docs", lifespan=lifespan)

    from fastapi_app.routes import api_routes

    app.include_router(api_routes.router)

    return app
