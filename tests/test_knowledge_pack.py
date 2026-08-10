import json
from pathlib import Path

from nova.knowledge_pack import KnowledgePack, build_pack


def test_pack_reads_entries_without_full_extraction(tmp_path: Path):
    source = tmp_path / "manual.jsonl"
    source.write_text(json.dumps({"topic": "securement", "rule": "inspect"}) + "\n", encoding="utf-8")
    pack_path = tmp_path / "truck-0001.nkp.zip"

    build_pack(
        pack_path,
        [("manual.jsonl", source, "jsonl")],
        pack_id="truck-0001",
    )

    pack = KnowledgePack(pack_path)
    assert pack.names() == ["manual.jsonl"]
    rows = list(pack.iter_jsonl("manual.jsonl"))
    assert rows[0]["topic"] == "securement"
    assert pack.verify()["ok"] is True


def test_each_pack_is_independently_readable(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("FMCSA knowledge", encoding="utf-8")
    b.write_text("USPS knowledge", encoding="utf-8")

    first = tmp_path / "truck-0001.nkp.zip"
    second = tmp_path / "truck-0002.nkp.zip"
    build_pack(first, [("a.txt", a, "text")], pack_id="truck-0001")
    build_pack(second, [("b.txt", b, "text")], pack_id="truck-0002")

    assert KnowledgePack(first).read_text("a.txt") == "FMCSA knowledge"
    assert KnowledgePack(second).read_text("b.txt") == "USPS knowledge"
