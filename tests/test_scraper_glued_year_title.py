"""发布名“年份与分辨率粘连”时标题提取的回归测试。

背景：115 分享转存到接收夹后自动整理，若目录名形如
``The Terminal List黑狼 (20254K.HDR＆杜比视界 内封精修简英双语…``（括号未闭合、
年份与 4K 粘连），旧实现把整串发布参数当作片名，主查询搜不到 TMDB 条目，
条目一直留在接收夹。这里锁定“干净片名必须排在最前”的行为。
"""

from app.services.scraper import (
    _batch_item_query_payload,
    _extract_scraper_title_candidates,
    _is_scraper_technical_noise_candidate,
)

MESSY_FOLDER = (
    "The Terminal List黑狼 (20254K.HDR＆杜比视界 内封精修简英双语＆简中特效sup字幕"
)
EPISODE_FILES = [
    {"name": "The.Terminal.List.Dark.Wolf.S01E0%d.2025.2160p.AMZN.WEB-DL.H2.mkv" % index}
    for index in range(1, 8)
]


def test_glued_year_folder_keeps_clean_title_first():
    candidates = _extract_scraper_title_candidates(MESSY_FOLDER)
    assert "The Terminal List黑狼" in candidates
    # 干净候选必须全部排在带发布参数的候选之前；首查询不能是整串发布参数。
    assert _is_scraper_technical_noise_candidate(candidates[0]) is False
    first_noisy = next(
        (i for i, item in enumerate(candidates) if _is_scraper_technical_noise_candidate(item)),
        len(candidates),
    )
    assert all(
        not _is_scraper_technical_noise_candidate(item) for item in candidates[:first_noisy]
    )


def test_glued_year_batch_query_uses_clean_title():
    query, media_type, year, variants = _batch_item_query_payload(
        {"name": MESSY_FOLDER}, EPISODE_FILES
    )
    assert media_type == "tv"
    assert year == "2025"
    for token in ("杜比", "双语", "sup", "20254K"):
        assert token not in query
    assert "The Terminal List黑狼" in variants
    assert variants[0] == query


def test_technical_noise_candidates_are_demoted_not_dropped():
    candidates = _extract_scraper_title_candidates(MESSY_FOLDER)
    noisy = [item for item in candidates if _is_scraper_technical_noise_candidate(item)]
    assert noisy, "带发布参数的候选应保留在末尾作为兜底"
    clean_zone = candidates[: len(candidates) - len(noisy)]
    assert all(not _is_scraper_technical_noise_candidate(item) for item in clean_zone)


def test_regressions_on_plain_release_names():
    assert _extract_scraper_title_candidates("Oppenheimer.2023.2160p.UHD.BluRay.x265")[0] == "Oppenheimer"
    assert _extract_scraper_title_candidates("Breaking Bad S01E01 1080p BluRay")[0] == "Breaking Bad"
    assert _extract_scraper_title_candidates("三体 第二季 [全 8 集] 4K HDR 简中")[0] == "三体"
