import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

async def main():
    eng = create_async_engine(
        "postgresql+asyncpg://agentp:agentp_dev@localhost:5432/agent_platform",
        poolclass=NullPool,
    )
    async with eng.connect() as conn:
        r = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='memory_assets' ORDER BY ordinal_position")
        )
        for row in r:
            print(row[0])
    await eng.dispose()

asyncio.run(main())
