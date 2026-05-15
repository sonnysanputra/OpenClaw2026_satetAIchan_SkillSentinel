import asyncio
from services.skillshub import fetch_skills
async def main():
    res = await fetch_skills()
    print("Total parsed skills:", len(res))
    if len(res) > 0:
        print("First 2 skills:", res[:2])
asyncio.run(main())
