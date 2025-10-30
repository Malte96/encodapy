#!/usr/bin/env python3
"""Generate a README copy for Sphinx docs with repository-relative links replaced
by absolute GitHub URLs so Sphinx doesn't treat them as missing internal docs.

This is a small, best-effort preprocessor. It resolves relative links that start
with ./ or ../ and rewrites them to point to the repository's GitHub tree on the
`main` branch. Adjust REPO_BASE and BRANCH if needed.
"""
from pathlib import Path
import re
import sys


REPO_OWNER = "gewv-tu-dresden"
REPO_NAME = "encodapy"
BRANCH = "main"

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Generate README copy for docs with rewritten links")
    parser.add_argument("--owner", help="GitHub repo owner/organization", default=REPO_OWNER)
    parser.add_argument("--repo", help="GitHub repository name", default=REPO_NAME)
    parser.add_argument("--branch", help="GitHub branch (or tag)", default=BRANCH)
    args = parser.parse_args(argv)

    owner = args.owner
    repo = args.repo
    branch = args.branch

    def make_github_url_local(rel_path: str) -> str:
        p = Path(rel_path)
        return f"https://github.com/{owner}/{repo}/blob/{branch}/{p.as_posix()}"

    # Find the nearest ancestor that contains README.md (robust in different CWDs)
    current = Path(__file__).resolve()
    repo_root = None
    for parent in [current] + list(current.parents):
        candidate = parent / "README.md"
        if candidate.exists():
            repo_root = parent
            readme_src = candidate
            break

    if repo_root is None:
        print("README.md not found in any parent directories starting from:", current, file=sys.stderr)
        sys.exit(1)

    out_dir = repo_root / "docs" / "source" / "_generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "README_FOR_DOCS.md"

    text = readme_src.read_text(encoding="utf-8")

    # local rewrite function that uses the CLI-supplied values
    def rewrite_links_local(text: str, src_dir: Path) -> str:
        pattern = re.compile(r"\((?P<target>(?:\.{1,2}/)[^)]+)\)")

        def repl(m):
            target = m.group("target")
            resolved = (src_dir / target).resolve()
            try:
                rel_to_repo = resolved.relative_to(repo_root)
            except Exception:
                rel_to_repo = Path(target)
            url = make_github_url_local(rel_to_repo.as_posix())
            return f"({url})"

        # also replace bare filenames like (LICENSE) or (dockerfile)
        bare_pattern = re.compile(r"\((?P<target>[A-Za-z0-9_\-\.]+)\)")

        def repl_bare(m):
            target = m.group("target")
            # skip if it looks like a URL or has a slash
            if "://" in target or "/" in target:
                return f"({target})"
            # if file exists at repo root, convert to github url
            candidate = repo_root / target
            if candidate.exists():
                url = make_github_url_local(Path(target).as_posix())
                return f"({url})"
            return f"({target})"

        text = pattern.sub(repl, text)
        text = bare_pattern.sub(repl_bare, text)
        return text

    new_text = rewrite_links_local(text, readme_src.parent)
    out_file.write_text(new_text, encoding="utf-8")
    print("Wrote", out_file)


if __name__ == "__main__":
    main()
