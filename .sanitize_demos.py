import re, pathlib
p = pathlib.Path("assets/demos/generate_all_demos.py")
text = p.read_text(encoding="utf-8")
PREFIX = r"C:\Users\sihat\Downloads\bones-seed"
def repl(m):
    rel = m.group(1)
    # Strip leading backslash from the captured tail so os.path.join doesn't
    # treat it as an absolute path; keep it a raw string for readability.
    rel = rel.lstrip("\\")
    return 'os.path.join(BONES_SEED, r"' + rel + '")'
pattern = re.compile(r'r"' + re.escape(PREFIX) + r'([^"]*)"')
new_text, n = pattern.subn(repl, text)
p.write_text(new_text, encoding="utf-8")
print(f"replaced {n} occurrences")
