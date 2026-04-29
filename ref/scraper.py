#!/usr/bin/env python3
"""MiniMax API Documentation Scraper

Downloads all API reference docs from platform.minimaxi.com
and organizes them by category into ref/api/* directories.
"""

import os
import re
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call(["pip", "install", "requests"])
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4...")
    import subprocess
    subprocess.check_call(["pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

BASE_URL = "https://platform.minimaxi.com"
LLMS_TXT_URL = f"{BASE_URL}/docs/llms.txt"

CATEGORIES = {
    "text": ["text-chat", "text-post", "text-prompt", "text-ai-sdk", "text-anthropic", "text-openai", "text/"],
    "voice": ["speech-", "voice-cloning", "voice-management", "voice-design"],
    "video": ["video-generation", "video-agent"],
    "image": ["image-generation"],
    "music": ["music-", "lyrics-"],
    "file": ["file-management"],
}

CATEGORY_DIRS = {
    "text": "ref/api/text",
    "voice": "ref/api/voice",
    "video": "ref/api/video",
    "image": "ref/api/image",
    "music": "ref/api/music",
    "file": "ref/api/file",
}


def determine_category(url_path: str) -> str:
    """Determine which category a URL belongs to."""
    for category, patterns in CATEGORIES.items():
        for pattern in patterns:
            if pattern in url_path:
                return category
    return "other"


def fetch_page(url: str, timeout: int = 30) -> tuple[str, str] | tuple[None, None]:
    """Fetch a page and return (content, error)."""
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response.raise_for_status()
        return response.text, None
    except Exception as e:
        return None, str(e)


def parse_llms_txt(content: str) -> list[tuple[str, str]]:
    """Parse llms.txt and extract all API reference links."""
    links = []
    pattern = r'\[([^\]]+)\]\((https?://[^\)]+\.md)\)'
    for match in re.finditer(pattern, content):
        title, url = match.group(1), match.group(2)
        if "/api-reference/" in url:
            links.append((title, url))
    return links


def clean_markdown_content(content: str) -> str:
    """Clean up markdown content - remove AgentInstructions and redirect headers."""
    # Remove AgentInstructions block if present
    start = content.find('<AgentInstructions>')
    end = content.find('</AgentInstructions>')
    if start >= 0 and end >= 0:
        content = content[:start] + content[end+20:]

    # Skip any leading metadata/redirect blocks before the first real heading
    lines = content.split('\n')
    cleaned_lines = []
    skip_until_content = True

    for line in lines:
        if skip_until_content:
            # Skip lines that are part of redirect metadata (lines starting with >)
            if line.startswith('# ') or line.startswith('```'):
                skip_until_content = False
                cleaned_lines.append(line)
            elif not line.strip() or line.startswith('>'):
                continue  # skip empty lines and quote blocks
            elif line.strip().startswith('#'):
                skip_until_content = False
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def sanitize_filename(title: str) -> str:
    """Convert title to a safe filename while preserving Chinese and ASCII alphanumeric."""
    # Keep alphanumeric (including ASCII letters), Chinese chars, spaces, dashes
    cleaned = ''
    for c in title:
        # Keep if alphanumeric (works for Chinese too), space, dash, underscore
        if c.isalnum() or c in ' _-':
            cleaned += c
        elif ord(c) > 127:  # Chinese/other non-ASCII
            cleaned += c
        else:
            cleaned += '_'
    # Replace spaces with underscores, clean up consecutive underscores
    cleaned = re.sub(r'\s+', '_', cleaned)
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_')
    return cleaned


def get_markdown_content(title: str, url: str) -> str:
    """Get the actual markdown content for a page."""
    md_url = url
    md_content, md_error = fetch_page(md_url)

    if md_error or not md_content:
        return ""

    # Remove AgentInstructions block if present
    start = md_content.find('<AgentInstructions>')
    end = md_content.find('</AgentInstructions>')
    if start >= 0 and end >= 0:
        md_content = md_content[:start] + md_content[end+20:]

    # Check if it's real markdown content
    if '```yaml' in md_content or 'openapi:' in md_content.lower():
        # Skip lines before the first real heading (# at start of line)
        lines = md_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# '):
                return '\n'.join(lines[i:])
        return md_content

    return md_content


def save_doc(title: str, url: str, category: str, output_dir: Path) -> bool:
    """Download and save a documentation page."""
    markdown_content = get_markdown_content(title, url)
    if not markdown_content:
        print(f"  [FAIL] {title}: no content retrieved")
        return False

    safe_name = sanitize_filename(title)
    output_file = output_dir / f"{safe_name}.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source: {url.replace('.md', '')}\n\n")
        f.write(markdown_content)

    print(f"  [OK] {category}/{output_file.name}")
    return True


def main():
    print("Fetching documentation index...")
    content, error = fetch_page(LLMS_TXT_URL)
    if error:
        print(f"Failed to fetch {LLMS_TXT_URL}: {error}")
        return

    links = parse_llms_txt(content)
    print(f"Found {len(links)} API reference pages\n")

    # Create category directories
    for cat_dir in set(CATEGORY_DIRS.values()):
        Path(cat_dir).mkdir(parents=True, exist_ok=True)
    Path("ref/api/other").mkdir(parents=True, exist_ok=True)

    # Process each link
    results = {"success": 0, "failed": 0}
    for title, url in links:
        category = determine_category(url)
        output_dir = Path(CATEGORY_DIRS.get(category, "ref/api/other"))
        success = save_doc(title, url, category, output_dir)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"\nDone! Saved {results['success']} docs, {results['failed']} failed.")
    print(f"\nOutput structure:")
    for cat, dir_path in CATEGORY_DIRS.items():
        count = len(list(Path(dir_path).glob("*.md")))
        print(f"  ref/api/{cat}: {count} files")


if __name__ == "__main__":
    main()