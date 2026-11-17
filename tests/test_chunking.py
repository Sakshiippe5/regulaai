from regulaai.rag.chunking import chunk_policy, load_policies

SAMPLE = "# Title\nintro\n\n## 1. Governance\n1.1 Board approves.\n\n## 2. Vulnerability\n2.1 Yearly.\n"


def test_splits_on_headings(tmp_path):
    f = tmp_path / "p.md"
    f.write_text(SAMPLE, encoding="utf-8")
    chunks = chunk_policy(f)
    assert [c.section for c in chunks] == ["1. Governance", "2. Vulnerability"]
    assert chunks[0].id == "p:1"
    assert "Board approves" in chunks[0].text
    assert "Yearly" not in chunks[0].text


def test_load_policies_reads_all_files(tmp_path):
    (tmp_path / "a.md").write_text("## 1. X\nfoo", encoding="utf-8")
    (tmp_path / "b.md").write_text("## 1. Y\nbar", encoding="utf-8")
    assert len(load_policies(tmp_path)) == 2