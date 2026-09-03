import asyncio
from sqlalchemy import select
from app.core.db import AsyncSessionLocal
from app.db.models import User, Library,DocumentChunk

async def query_and_show():
    print("🚀 Kết nối vào Database và lấy dữ liệu...\n")
    
    async with AsyncSessionLocal() as session:
        # Lấy danh sách Users
        # user_result = await session.execute(select(User))
        # users = user_result.scalars().all()
        
        # print(f"👤 TÌM THẤY {len(users)} USERS:")
        # print("-" * 50)
        # for u in users:
        #     print(f"- ID: {u.id}")
        #     print(f"  Email: {u.email}")
        #     print(f"  Tên: {u.first_name} {u.last_name}")
        #     print(f"  Ngày tạo: {u.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        #     print()
            
        # # Lấy danh sách Libraries
        # lib_result = await session.execute(select(Library))
        # libraries = lib_result.scalars().all()
        
        # print(f"📚 TÌM THẤY {len(libraries)} LIBRARIES:")
        # print("-" * 50)
        # for lib in libraries:
        #     print(f"- ID: {lib.id}")
        #     print(f"  Tên Thư viện: {lib.name}")
        #     print(f"  Mô tả: {lib.description}")
        #     print(f"  User ID (Chủ sở hữu): {lib.user_id}")
        #     print(f"  Số tài liệu: {lib.total_documents}")
        #     print()

# class DocumentChunk(Base):
#     __tablename__ = "document_chunks"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False)
#     document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     page_number = Column(Integer)
#     chunk_index = Column(Integer)
#     content = Column(Text, nullable=False)
#     embedding = Column(Vector(768))  # pgvector 768-dim (text-embedding-004)
#     meta_data = Column("metadata", JSONB)

#     document = relationship("Document", back_populates="chunks")
        lib_result = await session.execute(select(DocumentChunk))
        libraries = lib_result.scalars().all()
        
        print(f"📚 TÌM THẤY {len(libraries)} LIBRARIES:")
        print("-" * 50)
        for lib in libraries:
            print(f"- ID: {lib.id}")
            print(f"  Tên Thư viện: {lib.user_id}")
            print(f"  Mô tả: {lib.page_number}")
            print(f"  User ID (Chủ sở hữu): {lib.chunk_index}")
            print(f"  Số tài liệu: {lib.embedding}")
            print()
if __name__ == "__main__":
    asyncio.run(query_and_show())
