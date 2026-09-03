import asyncio
from sqlalchemy import text
from app.core.db import AsyncSessionLocal

async def migrate():
    print("Bat dau migration: Nang cap pgvector len 2048 chieu...")
    async with AsyncSessionLocal() as session:
        # Xóa các chunk cũ vì các vector cũ là 768 chiều không thể ép kiểu sang 2048
        await session.execute(text("TRUNCATE TABLE document_chunks CASCADE;"))
        print("Da don dep cac chunk cu 768 chieu")

        # Xóa index cũ
        await session.execute(text("DROP INDEX IF EXISTS idx_chunks_embedding;"))
        print("Da xoa index cu")

        # Đổi kiểu cột sang vector(2048)
        await session.execute(text("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(2048);"))
        print("Da nang cap cot embedding len vector(2048)")

        await session.commit()
    print("MIGRATION THANH CONG!")

if __name__ == "__main__":
    asyncio.run(migrate())
