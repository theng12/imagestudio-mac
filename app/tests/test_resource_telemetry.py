from pathlib import Path

from PIL import Image

from backend import generation, resource_telemetry
from backend.generation import GenerationJob, GenerationManager


class FakeSampler:
    instances = []

    def __init__(self, publish):
        self.publish = publish
        self.finished = None
        self.__class__.instances.append(self)

    def start(self):
        self.publish({"schema": "imagestudio.resource-telemetry", "phase": "running"})
        return self

    def finish(self, **kwargs):
        self.finished = kwargs
        payload = {
            "schema": "imagestudio.resource-telemetry",
            "schema_version": 1,
            "outcome": kwargs,
        }
        self.publish(payload)
        return payload


def test_sampler_reports_matching_image_schema(monkeypatch) -> None:
    snapshots = iter(
        [
            {
                "at": 1.0,
                "host": {
                    "total_gb": 8.59,
                    "available_gb": 4.0,
                    "used_gb": 4.0,
                    "used_percent": 53.0,
                    "pressure": {"supported": True, "raw": 1, "level": "normal"},
                    "swap_used_gb": 0.2,
                    "swap_in_bytes": 10,
                    "swap_out_bytes": 20,
                },
                "worker": {"rss_gb": 0.1, "process_count": 1},
                "mlx": {
                    "supported": True,
                    "active_gb": 0.0,
                    "cache_gb": 0.0,
                    "reported_peak_gb": 0.0,
                },
            },
            {
                "at": 2.0,
                "host": {
                    "total_gb": 8.59,
                    "available_gb": 1.5,
                    "used_gb": 6.5,
                    "used_percent": 82.0,
                    "pressure": {"supported": True, "raw": 2, "level": "warning"},
                    "swap_used_gb": 0.4,
                    "swap_in_bytes": 30,
                    "swap_out_bytes": 40,
                },
                "worker": {"rss_gb": 3.0, "process_count": 2},
                "mlx": {
                    "supported": True,
                    "active_gb": 4.5,
                    "cache_gb": 0.5,
                    "reported_peak_gb": 4.5,
                },
            },
        ]
    )
    last = None

    def snapshot(**_kwargs):
        nonlocal last
        try:
            last = next(snapshots)
        except StopIteration:
            pass
        return last

    monkeypatch.setattr(resource_telemetry, "_snapshot", snapshot)
    published = []
    sampler = resource_telemetry.JobResourceSampler(
        published.append, interval_seconds=60
    ).start()
    sampler._take()
    result = sampler.finish(
        state="done",
        memory_failure=False,
        restart_scheduled=False,
        model_retained=False,
    )

    assert result["schema"] == "imagestudio.resource-telemetry"
    assert result["host"]["minimum_available_gb"] == 1.5
    assert result["host"]["peak_pressure_level"] == "warning"
    assert result["mlx"]["reported_peak_gb"] == 4.5
    assert result["outcome"]["state"] == "done"
    assert published[-1] == result


def test_local_generation_publishes_resource_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    FakeSampler.instances.clear()
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(generation, "HISTORY_FILE", tmp_path / ".history.json")
    monkeypatch.setattr(generation, "MFLUX_AVAILABLE", True)
    monkeypatch.setattr(generation.memory_policy, "mark_generation_started", lambda: None)
    monkeypatch.setattr(generation.memory_policy, "mark_generation_finished", lambda: None)
    monkeypatch.setattr(
        generation.resource_telemetry, "JobResourceSampler", FakeSampler
    )
    manager = GenerationManager()
    job = GenerationJob(
        job_id="telemetry-image",
        mode="txt2img",
        params={"repo": "owner/model", "steps": 4},
        total_steps=4,
    )

    def render(_job, output_path):
        _job.resolved_seed = 7
        Image.new("RGB", (64, 64), "violet").save(output_path, format="PNG")

    monkeypatch.setattr(manager, "_dispatch_txt2img", render)
    manager._run_txt2img(job)

    assert job.state == "done"
    assert job.serialize()["resource_telemetry"] == {
        "schema": "imagestudio.resource-telemetry",
        "schema_version": 1,
        "outcome": {
            "state": "done",
            "memory_failure": False,
            "restart_scheduled": False,
            "model_retained": False,
        },
    }
    assert FakeSampler.instances[0].finished["state"] == "done"
