import asyncio
from sqlalchemy import text
from src.database.connection import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text("SELECT email, authority_type FROM authorities ORDER BY authority_level DESC, email LIMIT 20"))
        rows = r.fetchall()
        print('Found', len(rows), 'authorities (showing up to 20):')
        for row in rows:
            print(' -', row[0], '|', row[1])

if __name__ == '__main__':
    asyncio.run(check())
