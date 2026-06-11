import json

import fitz
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app


# ── in-memory SQLite DB for every test ───────────────────────────────────────

@pytest.fixture(autouse=True)
def db_setup(monkeypatch):
    from contextlib import contextmanager

    import app.db.session as db_mod
    import app.models  # noqa: F401 — registers all ORM models
    from app.models.base import Base

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    @contextmanager
    def _test_db_session():
        db = TestSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # Patch engine so lifespan's create_tables() also uses the test DB
    monkeypatch.setattr(db_mod, "engine", test_engine)
    # Patch db_session at the module level — document_store uses _db.db_session()
    monkeypatch.setattr(db_mod, "db_session", _test_db_session)
    yield


# ── in-memory Qdrant for every test ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def in_memory_vector_store():
    from app.services.vector_store import vector_store
    vector_store._client = QdrantClient(":memory:")
    yield
    vector_store._client = None


# ── mock OpenAI embeddings ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    import app.services.embeddings as emb

    def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
        from app.core.config import settings
        return [[0.1] * settings.embedding_dimensions for _ in texts]

    def _fake_embed_text(text: str) -> list[float]:
        from app.core.config import settings
        return [0.1] * settings.embedding_dimensions

    monkeypatch.setattr(emb, "embed_texts", _fake_embed_texts)
    monkeypatch.setattr(emb, "embed_text", _fake_embed_text)


# ── mock LLM ──────────────────────────────────────────────────────────────────

_QUIZ_TEXT_MOCK = """\
题目：请描述文档的核心主题
答案：测试答案
解析：测试解析
知识点：test_concept
"""

# Two MC mocks with DIFFERENT knowledge_points so mastery updates don't interfere
_MC_TEXT_MOCKS = [
    """\
题目：以下哪项是监督学习的常见算法
A：线性回归
B：K-means
C：PCA
D：DBSCAN
答案：A
解析：线性回归是监督学习算法
知识点：监督学习
""",
    """\
题目：以下哪项是深度学习的模型架构
A：CNN
B：K-means
C：SVM
D：DBSCAN
答案：A
解析：CNN是深度学习的常用架构
知识点：深度学习
""",
]


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    import app.services.llm as llm

    mc_counter = [0]  # reset per test invocation

    def _mock_call_chat(messages, **_):
        user_msg = next(
            (m.get("content", "") for m in messages if m.get("role") == "user"), ""
        )
        if "出1道新的单选题" in user_msg or "出1道中文单选题" in user_msg:
            idx = mc_counter[0] % len(_MC_TEXT_MOCKS)
            mc_counter[0] += 1
            return _MC_TEXT_MOCKS[idx]
        if "出1道新的简答题" in user_msg or "出1道中文简答题" in user_msg:
            return _QUIZ_TEXT_MOCK
        return "这是一个较长的测试回答，根据文档内容整理，涵盖主要知识点，供单元测试验证使用。"

    def _mock_stream_chat(messages, **_):
        yield "这是一个较长的流式测试回答，根据文档内容整理，涵盖主要知识点，供单元测试验证使用。"

    def _mock_stream_answer(question, chunks, **_):
        yield "这是一个较长的测试回答，根据文档内容整理，涵盖主要知识点，供单元测试验证使用。"

    def _mock_decide_retrieval(question: str) -> tuple[bool, str]:
        # Default: always retrieve (safe path) so existing tests are unaffected
        return True, question

    monkeypatch.setattr(llm, "call_chat", _mock_call_chat)
    monkeypatch.setattr(llm, "stream_chat", _mock_stream_chat)
    monkeypatch.setattr(llm, "stream_answer_question", _mock_stream_answer)
    monkeypatch.setattr(llm, "decide_retrieval", _mock_decide_retrieval)
    monkeypatch.setattr(
        llm,
        "call_chat_json",
        lambda messages, **_: json.dumps({}),
    )


# ── shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def valid_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a test PDF document with sample learning content.")
    return doc.tobytes()


@pytest.fixture
def valid_pdf_path(tmp_path, valid_pdf_bytes):
    path = tmp_path / "test.pdf"
    path.write_bytes(valid_pdf_bytes)
    return path


@pytest.fixture
def uploaded_doc_id(client, valid_pdf_bytes) -> str:
    resp = client.post(
        "/documents/upload",
        files={"file": ("lecture.pdf", valid_pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["document"]["id"]
    # Background tasks run synchronously in TestClient; poll until final status.
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            break
    assert status == "ready"
    return doc_id
