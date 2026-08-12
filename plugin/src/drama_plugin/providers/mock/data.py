from dataclasses import dataclass, field

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.contracts.research import ResearchEvidence, ResearchSource


@dataclass
class MockDramaData:
    work: Work = field(default_factory=lambda: Work(id="work-1", title="神都密诏", description="武周时期历史悬疑短剧", content={"theme": "权力与信任"}))
    script: Script = field(default_factory=lambda: Script(id="script-1", work_id="work-1", title="神都密诏·短剧剧本", content={"mainLine": "狄仁杰追查改变朝局的密诏"}))
    episode: Episode = field(default_factory=lambda: Episode(id="episode-1", script_id="script-1", number=1, title="夜访书房", content={"hook": "密诏线索在雨夜浮现"}))
    scene: Scene = field(default_factory=lambda: Scene(id="scene-1", episode_id="episode-1", number=3, heading="内景·狄府书房·夜", content={"goal": "辨认残缺密诏", "characters": ["狄仁杰"]}))
    shot: Shot = field(default_factory=lambda: Shot(id="shot-1", scene_id="scene-1", number=2, description="中近景，狄仁杰抬眼看向窗外闪电，手中密诏微颤。", duration_seconds=4.0, content={"framing": "MCU"}))
    assets: list[Asset] = field(default_factory=lambda: [
        Asset(id="asset-di", asset_type=AssetType.CHARACTER, name="狄仁杰标准人物", description="沉静、敏锐，武周官服", reference_media_ids=["media-di"]),
        Asset(id="asset-study", asset_type=AssetType.LOCATION, name="张柬之府邸书房", description="木构书房，烛火与雨夜冷光交叠", reference_media_ids=["media-study"]),
    ])
    media: list[Media] = field(default_factory=lambda: [
        Media(id="media-di", media_type=MediaType.IMAGE, mime_type="image/png", storage_key="mock/media/di-renjie.png", metadata={"width": 1024, "height": 1024}),
        Media(id="media-study", media_type=MediaType.IMAGE, mime_type="image/png", storage_key="mock/media/study.png", metadata={"width": 1024, "height": 1024}),
    ])
    source: ResearchSource = field(default_factory=lambda: ResearchSource(title="旧唐书·狄仁杰传", citation="《旧唐书》卷八十九", source_type="PRIMARY_TEXT"))
    evidence: ResearchEvidence = field(init=False)

    def __post_init__(self) -> None:
        self.evidence = ResearchEvidence(claim="狄仁杰曾任宰相并以直谏著称", excerpt="契丹扰冀州时，狄仁杰被起用处理军政。", source=self.source, confidence=0.88, tags=["狄仁杰", "武周"])
