"""Registry of candidate content sources (DOC-10 acquisition). Facts below were read from the cited pages on 2026-11-08;
anything not stated there is recorded as 'unverified' rather than assumed."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SourceInfo:
    source_id: str
    name: str
    url: str
    license: str
    commercial_use: Optional[bool]          # None = unverified
    redistribution: Optional[bool]
    scientific_credibility: str             # none | unverified | ...
    copyright_notes: str
    quality_notes: str
    localization: str
    decision: str


SOURCES = {
    "authored_unreviewed": SourceInfo("authored_unreviewed", "Project-authored starter text (AI-drafted)", "n/a", "project-owned", True, True, "none",
        "Written for this project; no third-party text copied.", "General knowledge only; NOT expert reviewed; no citations.",
        "FA/EN names drafted; FA unreviewed", "Allowed only as draft/experimental; never publishable without expert review + sources"),
    "free_exercise_db": SourceInfo("free_exercise_db", "yuhonas/free-exercise-db", "https://github.com/yuhonas/free-exercise-db", "Unlicense (repo); image license not stated",
        None, None, "unverified",
        "README says data derives from wrkout/exercises.json whose own license/provenance was NOT verified; images' license not stated.",
        "800+ exercises; fields: id,name,force,level,mechanic,equipment,primaryMuscles,secondaryMuscles,instructions,category,images; force/mechanic/equipment incomplete.",
        "English only", "Importer supported; do NOT import for publication until upstream provenance is verified; never use its images"),
    "wger": SourceInfo("wger", "wger Workout Manager", "https://wger.readthedocs.io/", "Software AGPL-3+; initial exercise data CC BY-SA 3.0; docs CC BY-SA 4+",
        None, None, "unverified",
        "CC BY-SA requires attribution and share-alike (derived databases must be shared under the same terms) - needs legal review before commercial use. Some images from Wikipedia with per-file SOURCES.",
        "Community-maintained; no clinical review stated.", "Multi-language (to verify)", "Not imported; blocked pending legal review (OPEN-004/007)"),
    "mifflin_1990": SourceInfo("mifflin_1990", "Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO. Am J Clin Nutr 1990;51(2):241-7",
        "https://insight.jci.org/references/scholar/5796/B66", "published paper (citation only)", True, False, "peer-reviewed; population: healthy adults",
        "Formula only is used (facts are not copyrightable); no text copied.", "Authors/journal/year verified from the cited page; volume/pages from prior knowledge - verify in PubMed.",
        "n/a", "Used for BMR estimate with stated uncertainty"),
}
