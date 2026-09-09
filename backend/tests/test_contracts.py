from app.schemas.contracts import SceneBreakdown, EditDecision

def test_scene_contract():
    scene = SceneBreakdown(scene_id="scene_01", number=1, title="Opening", description="Opening shot")
    assert scene.scene_id == "scene_01"

def test_editor_contract():
    decision = EditDecision(scene_id="scene_01", selected_takes=["take_01"])
    assert decision.selected_takes == ["take_01"]
