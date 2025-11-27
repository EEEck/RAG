from app.schemas import (
    SearchRequest,
    LessonHit,
    VocabHit,
    SearchResponse,
    ConceptPack,
    ConceptPackRequest,
    ConceptPackResponse,
    GenerateItemsRequest,
    GeneratedItem,
    ScopeReport,
    GenerateItemsResponse,
)

def test_search_request_defaults():
    req = SearchRequest(query="test")
    assert req.query == "test"
    assert req.top_lessons == 5
    assert req.top_vocab == 5
    assert req.max_unit is None

def test_search_request_custom():
    req = SearchRequest(query="test", top_lessons=10, top_vocab=10, max_unit=3)
    assert req.query == "test"
    assert req.top_lessons == 10
    assert req.top_vocab == 10
    assert req.max_unit == 3

def test_lesson_hit():
    hit = LessonHit(id=1, lesson_code="L1", title="Lesson 1", unit=1, score=0.9)
    assert hit.id == 1
    assert hit.lesson_code == "L1"
    assert hit.title == "Lesson 1"
    assert hit.unit == 1
    assert hit.score == 0.9

def test_vocab_hit():
    hit = VocabHit(id=1, term="hello", lesson_code="L1", unit=1, score=0.8)
    assert hit.term == "hello"
    assert hit.lesson_code == "L1"
    assert hit.unit == 1
    assert hit.score == 0.8

def test_search_response():
    l_hit = LessonHit(id=1, lesson_code="L1", title="Lesson 1", unit=1, score=0.9)
    v_hit = VocabHit(id=1, term="hello", lesson_code="L1", unit=1, score=0.8)
    res = SearchResponse(lessons=[l_hit], vocab=[v_hit])
    assert len(res.lessons) == 1
    assert len(res.vocab) == 1
    assert res.lessons[0].id == 1

def test_concept_pack_defaults():
    cp = ConceptPack(vocab=["hello"])
    assert cp.vocab == ["hello"]
    assert cp.grammar_rules == []
    assert cp.themes == []

def test_concept_pack_request_defaults():
    req = ConceptPackRequest(textbook_id="TB1", lesson_code="L1")
    assert req.textbook_id == "TB1"
    assert req.lesson_code == "L1"
    assert req.request_text is None
    assert req.k_lessons == 8
    assert req.k_vocab == 50

def test_generate_items_request_defaults():
    cp = ConceptPack(vocab=["hello"])
    req = GenerateItemsRequest(textbook_id="TB1", lesson_code="L1", concept_pack=cp)
    assert req.count == 10
    assert req.item_types == ["mcq", "cloze"]
    assert req.difficulty == "B1"

def test_generated_item_defaults():
    item = GeneratedItem(stem="Question?")
    assert item.stem == "Question?"
    assert item.options is None
    assert item.answer is None
    assert item.concept_tags == []
    assert item.uses_image is False

def test_scope_report_defaults():
    rep = ScopeReport(violations=0)
    assert rep.violations == 0
    assert rep.notes == []
