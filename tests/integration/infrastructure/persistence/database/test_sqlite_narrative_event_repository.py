"""SQLite Narrative Event Repository 集成测试"""
import pytest
import json
from pathlib import Path
from infrastructure.persistence.database.connection import DatabaseConnection
from infrastructure.persistence.database.sqlite_narrative_event_repository import (
    SqliteNarrativeEventRepository
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[5] / "infrastructure" / "persistence" / "database" / "schema.sql"
)


@pytest.fixture
def db():
    """内存数据库 fixture"""
    db = DatabaseConnection(":memory:")
    # 手动加载 schema（因为 DatabaseConnection 的 _ensure_database_exists 只在文件路径时加载）
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    db.get_connection().executescript(schema_sql)
    db.get_connection().commit()
    yield db
    db.close()


@pytest.fixture
def repository(db):
    """仓储 fixture"""
    return SqliteNarrativeEventRepository(db)


def test_list_up_to_chapter_empty(repository):
    """测试空数据库返回空列表"""
    events = repository.list_up_to_chapter("novel-1", 5)
    assert events == []


def test_append_and_list_events(repository, db):
    """测试插入事件后按 chapter_number ASC 排序"""
    # 先创建小说
    db.execute(
        "INSERT INTO novels (id, title, slug, target_chapters) VALUES (?, ?, ?, ?)",
        ("novel-1", "Test Novel", "test-novel", 10)
    )
    db.get_connection().commit()

    # 插入事件（乱序）
    mutations_1 = [{"entity_id": "char-1", "field": "location", "value": "城市A"}]
    mutations_2 = [{"entity_id": "char-1", "field": "status", "value": "受伤"}]
    mutations_3 = [{"entity_id": "char-2", "field": "mood", "value": "愤怒"}]

    event_id_3 = repository.append_event("novel-1", 3, "第三章事件", mutations_3)
    event_id_1 = repository.append_event("novel-1", 1, "第一章事件", mutations_1)
    event_id_2 = repository.append_event("novel-1", 2, "第二章事件", mutations_2)

    # 验证返回的 event_id 不为空
    assert event_id_1
    assert event_id_2
    assert event_id_3

    # 查询所有事件
    events = repository.list_up_to_chapter("novel-1", 10)
    assert len(events) == 3

    # 验证排序（按 chapter_number ASC）
    assert events[0]["chapter_number"] == 1
    assert events[0]["event_summary"] == "第一章事件"
    assert events[0]["event_id"] == event_id_1

    assert events[1]["chapter_number"] == 2
    assert events[1]["event_summary"] == "第二章事件"
    assert events[1]["event_id"] == event_id_2

    assert events[2]["chapter_number"] == 3
    assert events[2]["event_summary"] == "第三章事件"
    assert events[2]["event_id"] == event_id_3


def test_list_filters_by_chapter(repository, db):
    """测试只返回 chapter <= max_chapter 的事件"""
    # 先创建小说
    db.execute(
        "INSERT INTO novels (id, title, slug, target_chapters) VALUES (?, ?, ?, ?)",
        ("novel-1", "Test Novel", "test-novel", 10)
    )
    db.get_connection().commit()

    # 插入多个章节的事件
    repository.append_event("novel-1", 1, "第一章", [])
    repository.append_event("novel-1", 3, "第三章", [])
    repository.append_event("novel-1", 5, "第五章", [])
    repository.append_event("novel-1", 7, "第七章", [])

    # 查询到第 3 章
    events = repository.list_up_to_chapter("novel-1", 3)
    assert len(events) == 2
    assert events[0]["chapter_number"] == 1
    assert events[1]["chapter_number"] == 3

    # 查询到第 5 章
    events = repository.list_up_to_chapter("novel-1", 5)
    assert len(events) == 3
    assert events[2]["chapter_number"] == 5


def test_mutations_json_serialization(repository, db):
    """测试 mutations JSON 序列化/反序列化"""
    # 先创建小说
    db.execute(
        "INSERT INTO novels (id, title, slug, target_chapters) VALUES (?, ?, ?, ?)",
        ("novel-1", "Test Novel", "test-novel", 10)
    )
    db.get_connection().commit()

    # 复杂的 mutations 结构
    mutations = [
        {
            "entity_id": "char-1",
            "field": "attributes",
            "value": {"strength": 10, "intelligence": 15}
        },
        {
            "entity_id": "char-2",
            "field": "inventory",
            "value": ["sword", "shield", "potion"]
        }
    ]

    event_id = repository.append_event("novel-1", 1, "复杂事件", mutations)

    # 查询并验证反序列化
    events = repository.list_up_to_chapter("novel-1", 1)
    assert len(events) == 1

    retrieved_mutations = events[0]["mutations"]
    assert isinstance(retrieved_mutations, list)
    assert len(retrieved_mutations) == 2
    assert retrieved_mutations[0]["entity_id"] == "char-1"
    assert retrieved_mutations[0]["value"] == {"strength": 10, "intelligence": 15}
    assert retrieved_mutations[1]["value"] == ["sword", "shield", "potion"]
