from scripts.harness_lib import codex


def test_installed_tooling_and_python_cache_do_not_leak_into_distribution(tmp_path):
    source = tmp_path / "source"
    skill = source / "skills/example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: example\ndescription: Example tooling skill for isolated packaging tests.\n---\n# Example\n")
    (skill / "scripts").mkdir()
    (skill / "scripts/run.py").write_text("print('example')\n")
    (skill / "scripts/run.py").chmod(0o755)
    (skill / "scripts/__pycache__").mkdir()
    (skill / "scripts/__pycache__/run.pyc").write_bytes(b"nonportable runtime cache")
    (skill / "scripts/node_modules").mkdir()
    (skill / "scripts/node_modules/linked-package").symlink_to(tmp_path)
    (source / ".claude-plugin").mkdir()
    (source / ".claude-plugin/plugin.json").write_text('{"name":"ts","version":"1.0.0"}')
    destination = tmp_path / "target"
    codex.build(source, destination)
    resources = destination / "skills/example/scripts"
    assert (resources / "run.py").read_bytes() == (skill / "scripts/run.py").read_bytes()
    assert (resources / "run.py").stat().st_mode & 0o111
    assert not (resources / "__pycache__").exists()
    assert not (resources / "node_modules").exists()


def test_projection_reflows_expanded_prose_without_rewriting_code_or_frontmatter():
    from scripts.harness_lib.generated_tree import wrap_markdown_prose
    header = '---\ndescription: ' + 'detail ' * 45 + '\n---\n'
    code = '```typescript\nconst message = "' + 'keep ' * 50 + '";\n```\n'
    paragraph = '1. Inspect ' + 'the package resource and its evidence ' * 10 + '\n'
    transformed = wrap_markdown_prose(header + code + paragraph)
    assert transformed.startswith(header + code)
    body = transformed[len(header + code):]
    assert all(len(line) <= 200 for line in body.splitlines())
    assert ' '.join(body.split()) == ' '.join(paragraph.split())
    assert all(line.startswith('   ') for line in body.splitlines()[1:])


def test_projection_preserves_quoted_fenced_code_and_markdown_hard_breaks():
    from scripts.harness_lib.generated_tree import wrap_markdown_prose
    quoted_code = '> ```typescript\n> const text = "' + 'keep ' * 60 + '";\n> ```\n'
    assert wrap_markdown_prose(quoted_code) == quoted_code
    qualified_code = quoted_code.replace('keep ', '$typescript-starter:ts-review ', 1)
    assert codex._wrap_namespace_expanded_lines(qualified_code, 'typescript-starter') == qualified_code
    paragraph = 'Inspect the package and preserve the intended line break. ' * 6 + '  \nNext line.\n'
    transformed = wrap_markdown_prose(paragraph)
    assert transformed.endswith('  \nNext line.\n')
    assert all(len(line) <= 200 for line in transformed.splitlines())
