import asyncio
import sys
from sqlalchemy import select
from app.core.db import AsyncSessionLocal
from app.db.models import Library, DocumentChunk
from app.services.vector_store import similarity_search

async def run_similarity_test(query: str = "mạng máy tính là gì"):
    print("=" * 70)
    print("🚀 BẮT ĐẦU TEST TÌM KIẾM VECTOR (HyDE SIMILARITY SEARCH)")
    print("=" * 70)
    print(f"📌 Câu hỏi kiểm tra: \"{query}\"\n")

    async with AsyncSessionLocal() as session:
        # 1. Tìm thư viện có chứa document_chunks để test
        stmt = (
            select(DocumentChunk.library_id, DocumentChunk.user_id)
            .limit(1)
        )
        res = await session.execute(stmt)
        sample = res.first()

        if not sample:
            print("❌ Không tìm thấy bất kỳ chunk nào trong bảng `document_chunks`!")
            print("👉 Vui lòng tạo thư viện và upload tài liệu PDF trước khi chạy test.")
            return

        library_id = str(sample.library_id)
        user_id = str(sample.user_id)

        # Lấy thông tin chi tiết thư viện
        lib = await session.get(Library, sample.library_id)
        lib_name = lib.name if lib else "N/A"

        print(f"📚 Thư viện được chọn test:")
        print(f"   - ID: {library_id}")
        print(f"   - Tên: {lib_name}")
        print(f"   - User ID: {user_id}")
        print("-" * 70)

    # 2. Gọi hàm similarity_search với HyDE
    print("⏳ Đang sinh câu trả lời giả định và tìm kiếm vector trong pgvector...\n")
    results = await similarity_search(
        query=query,
        library_id=library_id,
        user_id=user_id,
        top_k=4,
    )

    # 3. Hiển thị kết quả
    print("\n" + "=" * 70)
    print(f"🎯 KẾT QUẢ TÌM THẤY: {len(results)} CHUNKS LIÊN QUAN NHẤT")
    print("=" * 70)

    if not results:
        print("⚠️ Không tìm thấy chunk nào phù hợp với câu hỏi.")
        return

    for i, c in enumerate(results, 1):
        score_percent = round(c['score'] * 100, 2)
        print(f"\n[#{i}] 📄 Trang {c['page_number']} | 🎯 Độ tương đồng: {score_percent}% | Chunk #{c['chunk_index']}")
        print(f"     ID: {c['id']}")
        print(f"     Document ID: {c['document_id']}")
        print(f"     📝 Nội dung đoạn văn:")
        # In nội dung cắt dòng đẹp
        content_lines = c['content'].strip().split("\n")
        preview = "\n".join(f"        {line}" for line in content_lines[:6])
        if len(content_lines) > 6:
            preview += "\n        ..."
        print(preview)

    print("\n" + "=" * 70)
    print("✅ TEST HOÀN TẤT THÀNH CÔNG!")
    print("=" * 70)

if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "mạng máy tính là gì"
    asyncio.run(run_similarity_test(test_query))
