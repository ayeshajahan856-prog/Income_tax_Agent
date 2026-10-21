"""Regenerates the results blocks in README.md and REPORT.md from results.json ONLY.
Run automatically by run_eval.py after a complete run. Can also be run by hand:  python make_report.py
Blocks live between <!-- RESULTS:START --> and <!-- RESULTS:END --> markers."""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def _fmt(n, d, pct):
    return f"{n}/{d} ({pct}%)" if d and pct is not None else "n/a"


def build_block(r: dict) -> str:
    lines = [
        f"_Auto-generated from `results.json` (run: {r['timestamp']}, model: `{r['model']}`, "
        f"{r['total_test_cases']} test cases, {r['ambiguous_cases_count']} ambiguous). Do not edit by hand._",
        "",
        "| Architecture | API errors | Math (numeric cases) | Section citation | Clarification (ambiguous) | Hallucinated section |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for name, s in r["summary_table"].items():
        m, d = r["metrics"][name], r["denominators"][name]
        lines.append(
            f"| {name} | {r['api_error_counts'][name]} "
            f"| {_fmt(m['correct_math'], d['math'], s['Math Accuracy (%)'])} "
            f"| {_fmt(m['correct_section'], d['section'], s['Section Citation Accuracy (%)'])} "
            f"| {_fmt(m['correct_clarification'] if 'correct_clarification' in m else m['clarification_handled'], d['clarification'], s['Clarification-First Rate (%)'])} "
            f"| {_fmt(m['hallucinations'], d['hallucination'], s['Hallucination Rate (%)'])} |"
        )
    c = r.get("agent_reply_consistency", {})
    if c.get("checked"):
        lines += ["", f"Agent reply text shows the tool's tax figure in {c['consistent']}/{c['checked']} non-zero cases."]
    lines += [
        "",
        "Notes: API errors / rate-limit failures are excluded from every denominator, never counted as wrong answers. "
        "Ground truth is hand-written in `evaluation.py` and depends on the rules in `rules.json`, which have not been "
        "checked against the official gazette. Hallucination = a cited section number that is not in this project's "
        "knowledge base (it does not prove the section is wrong in the real Act). Small sample (40 cases), single run.",
    ]
    return "\n".join(lines)


def _replace(path: Path, block: str):
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pat.search(text):
        return
    path.write_text(pat.sub(lambda _: f"{START}\n{block}\n{END}", text), encoding="utf-8")


def generate():
    r = json.loads((BASE / "results.json").read_text(encoding="utf-8"))
    if not r.get("complete"):
        raise RuntimeError("results.json is not a complete run - refusing to publish numbers")
    block = build_block(r)
    _replace(BASE / "README.md", block)
    _replace(BASE / "REPORT.md", block)


if __name__ == "__main__":
    generate()
    print("README.md and REPORT.md updated from results.json")
