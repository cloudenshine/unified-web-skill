"""Tests for app.pipeline.storage — ResultStorage."""

import json
import os
import pytest
from types import SimpleNamespace
from unittest.mock import patch

from app.pipeline.storage import ResultStorage
from app.models import ResearchTask, ResearchRecord, ResearchResult, ResearchStats


@pytest.fixture
def storage():
    return ResultStorage()


@pytest.fixture
def sample_result():
    task = ResearchTask(query="test query", task_id="test-id-123")
    records = [
        ResearchRecord(url="https://a.com", title="A", text="Content A " * 20, content_hash="hash_a"),
        ResearchRecord(url="https://b.com", title="B", text="Content B " * 20, content_hash="hash_b"),
    ]
    stats = ResearchStats(total_discovered=10, total_collected=2)
    return ResearchResult(
        task=task,
        records=records,
        stats=stats,
        queries_used=["test query", "test query expanded"],
    )


@pytest.fixture
def output_dir(tmp_path):
    """Use pytest's tmp_path for output."""
    return str(tmp_path / "test_outputs")


class TestSaveJson:
    @pytest.mark.asyncio
    async def test_creates_json_file(self, storage, sample_result, output_dir):
        files = await storage.save(sample_result, output_format="json", output_dir=output_dir)
        json_files = [f for f in files if f.endswith(".json") and "_manifest" not in f]
        assert len(json_files) == 1
        assert os.path.exists(json_files[0])

        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "task" in data or "records" in data

    @pytest.mark.asyncio
    async def test_manifest_created(self, storage, sample_result, output_dir):
        files = await storage.save(sample_result, output_format="json", output_dir=output_dir)
        manifest_files = [f for f in files if "_manifest.json" in f]
        assert len(manifest_files) == 1
        assert os.path.exists(manifest_files[0])


class TestSaveNdjson:
    @pytest.mark.asyncio
    async def test_creates_ndjson_file(self, storage, sample_result, output_dir):
        files = await storage.save(sample_result, output_format="ndjson", output_dir=output_dir)
        ndjson_files = [f for f in files if f.endswith(".ndjson")]
        assert len(ndjson_files) == 1
        assert os.path.exists(ndjson_files[0])

        with open(ndjson_files[0], "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 2  # 2 records
        for line in lines:
            json.loads(line)  # each line is valid JSON


class TestSaveMarkdown:
    @pytest.mark.asyncio
    async def test_creates_md_file(self, storage, sample_result, output_dir):
        files = await storage.save(sample_result, output_format="md", output_dir=output_dir)
        md_files = [f for f in files if f.endswith(".md")]
        assert len(md_files) == 1
        assert os.path.exists(md_files[0])

        with open(md_files[0], "r", encoding="utf-8") as f:
            content = f.read()
        assert "# Research Report" in content
        assert "test query" in content
        assert "Statistics" in content


class TestSaveUnknownFormat:
    @pytest.mark.asyncio
    async def test_unknown_defaults_to_json(self, storage, sample_result, output_dir):
        files = await storage.save(sample_result, output_format="csv", output_dir=output_dir)
        json_files = [f for f in files if f.endswith(".json") and "_manifest" not in f]
        assert len(json_files) == 1


class TestPathSanitization:
    @pytest.mark.asyncio
    async def test_task_id_sanitized(self, storage, output_dir):
        task = ResearchTask(query="test", task_id="../../etc/passwd")
        result = ResearchResult(task=task)
        files = await storage.save(result, output_format="json", output_dir=output_dir)
        # Path should not escape output_dir
        for f in files:
            assert os.path.dirname(f) == output_dir or os.path.abspath(os.path.dirname(f)) == os.path.abspath(output_dir)

    @pytest.mark.asyncio
    async def test_special_chars_in_task_id(self, storage, output_dir):
        task = ResearchTask(query="test", task_id="a/b\\c<d>e:f")
        result = ResearchResult(task=task)
        files = await storage.save(result, output_format="json", output_dir=output_dir)
        assert len(files) >= 1
        for f in files:
            assert os.path.exists(f)


class TestOutputDirCreation:
    @pytest.mark.asyncio
    async def test_creates_dir_if_not_exists(self, storage, sample_result, tmp_path):
        new_dir = str(tmp_path / "nested" / "output")
        files = await storage.save(sample_result, output_format="json", output_dir=new_dir)
        assert os.path.isdir(new_dir)
        assert len(files) >= 1
