from markdown_it import MarkdownIt
from yarl import URL
from pathlib import Path
from mdformat.renderer import MDRenderer

GITHUB_USER = "I-love-study"
GITHUB_REPO = "py-rotaeno-stablizer-gui"
GITHUB_BRANCH = "main"

def convert_relative_links(text: str) -> str:
    md = MarkdownIt()
    tokens = md.parse(text)

    # base URLs
    raw_base = URL("https://raw.githubusercontent.com/") / GITHUB_USER / GITHUB_REPO / GITHUB_BRANCH
    blob_base = URL("https://github.com/") / GITHUB_USER / GITHUB_REPO / "blob" / GITHUB_BRANCH

    for token in tokens:
        if token.type != "inline":
            continue

        for child in token.children or []:
            if child.type == "image":
                src = child.attrs.get("src", "")
                assert isinstance(src, str)
                if not URL(src).is_absolute():
                    abs_url = str(raw_base / src)
                    print(f"Replace {src} -> {abs_url}")
                    child.attrs["src"] = abs_url

            if child.type == "link_open":
                href = child.attrs.get("href", "")
                assert isinstance(href, str)
                if not URL(href).is_absolute():
                    new_url = blob_base / href
                    for idx, (k, v) in enumerate(child.attrs):
                        if k == "href":
                            print(f"Replace {href} -> {new_url}")
                            child.attrs[idx] = ("href", str(new_url))
                            break

    renderer = MDRenderer()
    output_markdown = renderer.render(tokens, {}, {})
    return output_markdown

if __name__ == "__main__":
    readme_path = Path("README.md")
    content = readme_path.read_text(encoding="utf-8")
    new_content = convert_relative_links(content)
    #readme_path = Path("README_NEW.md")
    readme_path.write_text(new_content, encoding="utf-8")
