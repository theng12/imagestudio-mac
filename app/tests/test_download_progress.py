"""Progress reporting must degrade to "unknown", never to nonsense.

Two failure modes are covered here, both observed live on 2026-08-06 while
Onyx-Z-Image-Turbo-4bit and ERNIE-Image-Turbo were downloading:

1. A stalled download decayed its speed EMA toward zero without reaching it.
   A denormal still passes `> 0`, so `remaining / speed` produced an ETA of
   8.47e+72 seconds.
2. A failed `repo_info` left `total_bytes` at 0 for the whole job, which
   suppresses both `percent` and `eta_seconds` until the download ends.
"""
import time

import pytest

from backend import downloads


def _job(repo="segmind/Segmind-Vega", *, total, speed, observed, monkeypatch):
    monkeypatch.setattr(downloads.cache, "disk_bytes", lambda _r: observed)
    monkeypatch.setattr(downloads.cache, "incomplete_bytes", lambda _r: 0)
    job = downloads.DownloadJob(job_id="j", repo=repo)
    job.state = "running"
    job.started_at = time.time() - 60      # past the 3 s warm-up guard
    job.total_bytes = total
    job._speed_bps = speed
    # dt < 0.5 s, so serialize() leaves _speed_bps alone and the ETA guard
    # is tested against exactly the speed we injected.
    job._last_speed_sample = (time.time(), observed)
    return job


def test_stalled_download_reports_no_eta_instead_of_an_absurd_one(monkeypatch):
    """The bug: a denormal speed passed `> 0` and produced ETAs of ~1e72 s."""
    job = _job(total=6_470_000_000, speed=1e-60, observed=336_000_000,
               monkeypatch=monkeypatch)
    out = job.serialize()

    assert out["eta_seconds"] is None
    # Progress itself must still be reported — only the ETA is unknowable.
    assert out["percent"] == pytest.approx(5.19, abs=0.01)


def test_trickle_below_a_kilobyte_per_second_reports_no_eta(monkeypatch):
    job = _job(total=6_470_000_000, speed=500.0, observed=336_000_000,
               monkeypatch=monkeypatch)
    assert job.serialize()["eta_seconds"] is None


def test_real_throughput_still_reports_an_eta(monkeypatch):
    """The guard must not suppress ETA on a healthy download."""
    job = _job(total=6_470_000_000, speed=20_000_000.0, observed=470_000_000,
               monkeypatch=monkeypatch)
    out = job.serialize()

    assert out["eta_seconds"] == pytest.approx(300.0, rel=0.01)
    assert out["speed_bps"] == 20_000_000.0


def test_speed_ema_floors_to_zero_when_no_bytes_arrive(monkeypatch):
    """Repeated samples with no new bytes must reach a true 0.0, not a denormal.

    Each sample multiplies the EMA by 0.7, so it approaches zero
    asymptotically. Without a floor it becomes a denormal that still passes a
    `> 0` test forever; with one it must actually arrive at 0.0.
    """
    monkeypatch.setattr(downloads.cache, "disk_bytes", lambda _r: 1_000)
    monkeypatch.setattr(downloads.cache, "incomplete_bytes", lambda _r: 0)
    job = downloads.DownloadJob(job_id="j", repo="segmind/Segmind-Vega")
    job.state = "running"
    job.started_at = time.time() - 60
    job.total_bytes = 6_470_000_000
    job._speed_bps = 900.0                       # already decaying

    for _ in range(40):                          # ~0.7**40 -> far below 1.0
        job._last_speed_sample = (time.time() - 1.0, 1_000)   # no new bytes
        out = job.serialize()
        assert out["eta_seconds"] is None        # never absurd on the way down

    assert job._speed_bps == 0.0


def test_unreachable_hf_api_falls_back_to_the_catalog_size(monkeypatch):
    """A failed repo_info must not blind the progress bar for the whole job."""
    monkeypatch.setattr(
        downloads, "HfApi",
        lambda: (_ for _ in ()).throw(RuntimeError("network unreachable")),
    )
    monkeypatch.setattr(downloads.settings, "get_hf_token", lambda: None)
    monkeypatch.setattr(downloads.cache, "ensure_hub_dir", lambda: None)
    monkeypatch.setattr(downloads, "snapshot_download", lambda **kw: "/tmp/x")
    monkeypatch.setattr(downloads.cache, "disk_bytes", lambda _r: 0)
    monkeypatch.setattr(downloads.cache, "incomplete_bytes", lambda _r: 0)

    manager = downloads.DownloadManager()
    job = downloads.DownloadJob(job_id="j", repo="segmind/Segmind-Vega")
    manager._run(job)

    # segmind/Segmind-Vega is 6.6 GB in the catalog.
    assert job.total_bytes == 6_600_000_000
    assert job.state == "done"


def test_repo_missing_from_the_catalog_reports_zero_not_a_crash(monkeypatch):
    assert downloads.DownloadManager._catalog_total_bytes("nobody/not-here") == 0
