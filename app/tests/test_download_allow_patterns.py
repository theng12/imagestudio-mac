"""The catalog's per-model download filter must actually reach the downloader.

`download_allow_patterns` trims repos that ship weights the diffusers loader
never reads — a root-level single-file checkpoint, fp16 duplicates — saving
7-21 GB per repo. The wiring shipped in 1.24.0, but every filtered download to
that point passed patterns to `snapshot_download` by hand, so the integrated
path through `DownloadManager` had never once executed. These tests exercise
both call sites with the network mocked out: no bytes are fetched, no model is
loaded, and nothing touches the HF cache.

The two call sites are deliberately covered separately because they consume the
same patterns differently:

- `_resolve_total_bytes` filters the HF file manifest to size the job.
- `_run` hands the patterns to `snapshot_download` to fetch.
"""
from types import SimpleNamespace

import pytest

from backend import catalog, downloads


# The only models that carry a filter today. Asserted against the catalog
# itself below, so this list cannot silently drift out of date.
FILTERED_REPOS = [
    "RunDiffusion/Juggernaut-XL-Lightning",
    "Lykon/dreamshaper-xl-lightning",
    "segmind/Segmind-Vega",
]


@pytest.fixture
def snapshot_calls(monkeypatch):
    """Neutralise every side effect in `_run`, capturing the download kwargs.

    `_resolve_total_bytes` is stubbed here so this fixture isolates the
    `snapshot_download` call site; the sizing site has its own test below.
    """
    calls: list[dict] = []

    def fake_snapshot_download(**kwargs):
        calls.append(kwargs)
        return "/tmp/imagestudio-test-snapshot"

    monkeypatch.setattr(downloads, "snapshot_download", fake_snapshot_download)
    monkeypatch.setattr(downloads.cache, "ensure_hub_dir", lambda: None)
    monkeypatch.setattr(downloads.settings, "get_hf_token", lambda: None)
    monkeypatch.setattr(
        downloads.DownloadManager, "_resolve_total_bytes",
        lambda self, repo, token: 0,
    )
    return calls


def _run_job(repo: str) -> downloads.DownloadJob:
    manager = downloads.DownloadManager()
    job = downloads.DownloadJob(job_id="test-job", repo=repo)
    manager._run(job)
    return job


@pytest.mark.parametrize("repo", FILTERED_REPOS)
def test_catalog_patterns_reach_snapshot_download(repo, snapshot_calls):
    """The gap this file exists to close: catalog filter -> real download call."""
    expected = catalog.get_model(repo).download_allow_patterns
    assert expected, f"{repo} is expected to carry a download filter"

    job = _run_job(repo)

    assert job.state == "done"
    assert len(snapshot_calls) == 1
    assert snapshot_calls[0]["repo_id"] == repo
    assert snapshot_calls[0]["allow_patterns"] == expected


def test_unfiltered_model_still_downloads_everything(snapshot_calls):
    """The 39 models without a filter must behave exactly as before this existed."""
    repo = "AITRADER/FLUX2-klein-4B-mlx-4bit"
    assert catalog.get_model(repo).download_allow_patterns is None

    job = _run_job(repo)

    assert job.state == "done"
    assert snapshot_calls[0]["allow_patterns"] is None


def test_repo_missing_from_the_catalog_downloads_everything(snapshot_calls):
    """An unknown repo must degrade to no filtering rather than fetching nothing."""
    repo = "nobody/not-in-the-catalog"
    assert catalog.get_model(repo) is None

    job = _run_job(repo)

    assert job.state == "done"
    assert snapshot_calls[0]["allow_patterns"] is None


def test_total_bytes_counts_only_the_files_the_filter_allows(monkeypatch):
    """The sizing call site must exclude what the download will skip.

    Otherwise the UI shows a total the download never intends to fetch, and
    progress can never reach 100%.
    """
    repo = "RunDiffusion/Juggernaut-XL-Lightning"
    siblings = [
        SimpleNamespace(rfilename="model_index.json", size=1_000),
        SimpleNamespace(rfilename="unet/diffusion_pytorch_model.safetensors",
                        size=5_000_000_000),
        SimpleNamespace(rfilename="vae/diffusion_pytorch_model.safetensors",
                        size=300_000_000),
        # The root-level single-file checkpoint diffusers never reads. This is
        # exactly the weight the filter exists to skip.
        SimpleNamespace(rfilename="Juggernaut_XL_Lightning.safetensors",
                        size=7_000_000_000),
    ]
    monkeypatch.setattr(
        downloads, "HfApi",
        lambda: SimpleNamespace(repo_info=lambda **kw: SimpleNamespace(siblings=siblings)),
    )
    monkeypatch.setattr(downloads.settings, "get_hf_token", lambda: None)

    total = downloads.DownloadManager()._resolve_total_bytes(repo, None)

    assert total == 1_000 + 5_000_000_000 + 300_000_000


def test_unfiltered_model_counts_every_file(monkeypatch):
    """Without a filter, sizing must include everything — unchanged behaviour."""
    repo = "AITRADER/FLUX2-klein-4B-mlx-4bit"
    siblings = [
        SimpleNamespace(rfilename="config.json", size=2_000),
        SimpleNamespace(rfilename="anything/at/all.safetensors", size=4_000_000_000),
    ]
    monkeypatch.setattr(
        downloads, "HfApi",
        lambda: SimpleNamespace(repo_info=lambda **kw: SimpleNamespace(siblings=siblings)),
    )
    monkeypatch.setattr(downloads.settings, "get_hf_token", lambda: None)

    total = downloads.DownloadManager()._resolve_total_bytes(repo, None)

    assert total == 2_000 + 4_000_000_000


def test_no_model_declares_an_empty_filter():
    """An empty tuple would make the two call sites disagree.

    `_resolve_total_bytes` guards with `if patterns`, so `()` is falsy and means
    "no filter" — it would size the whole repo. But `snapshot_download` treats
    `allow_patterns=()` as "match nothing" and would fetch zero files, reporting
    success. Keep the field either `None` or non-empty.
    """
    for model in catalog.CATALOG:
        patterns = model.download_allow_patterns
        assert patterns is None or len(patterns) > 0, (
            f"{model.repo} declares an empty download filter; use None instead"
        )
