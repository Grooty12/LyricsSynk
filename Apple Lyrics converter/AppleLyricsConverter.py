import sys, json, re, os


import re
from typing import List


def load_lyrics(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def convert_time_make_long(time):
    if len(time) == 5:
        return f"00:0{time}"
    elif len(time) == 6:
        return f"00:{time}"
    elif len(time) == 8:
        return f"0{time}"
    else:
        return time

def save_lyrics(file_path, string):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(string)

def import_lyrics(file_path):
    json_data = load_lyrics(file_path[1])
    mostly_lyrics = json_data.get("data")[0].get("attributes").get("ttmlLocalizations").split("</metadata>")[1]
    parts = re.split(r'(<p\b[^>]*>.*?</p>)', mostly_lyrics, flags=re.S)
    # every other element is the tag; filter empty strings
    chunks = [p for p in parts if p]
    return [p for p in chunks if p[0:3] == "<p "]

import re
from typing import List, Tuple

def parse_time(time_str: str) -> str:
    """Convert time format from seconds or MM:SS.mmm to MM:SS.mmm format."""
    if ':' in time_str:
        # Already in MM:SS.mmm format - ensure proper padding
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return f"{minutes:02d}:{seconds:06.3f}"
        return time_str

    # Convert from seconds to MM:SS.mmm
    seconds = float(time_str)
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:06.3f}"

def extract_spans_with_spaces(html_content: str) -> List[Tuple[str, str, str, bool]]:
    """Extract span elements with their text and space information."""
    span_pattern = r'<span begin="([^"]*)" end="([^"]*)">([^<]*)</span>(\s*)'
    matches = re.finditer(span_pattern, html_content)

    spans = []
    for match in matches:
        begin, end, text, trailing_space = match.groups()
        has_space = (trailing_space == " ")
        text = text.replace("(", "")
        text = text.replace(")", "")
        spans.append((begin, end, text, has_space))

    return spans

def build_lrc_text(spans: List[Tuple[str, str, str, bool]]) -> str:
    """Build LRC format text from spans."""
    result = []

    for i, (begin, end, text, has_space) in enumerate(spans):
        begin_time = parse_time(begin)
        end_time = parse_time(end)

        # Add word with start and end timestamps
        result.append(f"<{begin_time}>{text}<{end_time}>")

        # Add space if needed (but not after last word)
        if has_space and i < len(spans) - 1:
            result.append(" ")

    return ''.join(result)

def convert_to_lrc_format(strings: List[str]) -> List[str]:
    """Convert array of XML strings to LRC format."""
    results = []

    for string in strings:
        # Extract main attributes
        begin_match = re.search(r'begin="([^"]*)"', string)
        end_match = re.search(r'end="([^"]*)"', string)
        agent_match = re.search(r'ttm:agent="([^"]*)"', string)
        role_match = re.search(r'ttm:role="([^"]*)"', string)

        if not (begin_match and end_match):
            continue

        begin_time = parse_time(begin_match.group(1))
        end_time = parse_time(end_match.group(1))

        # Extract spans with space information
        spans = extract_spans_with_spaces(string)

        # Build LRC text
        text_content = build_lrc_text(spans)

        # Check if it's background vocals
        role = role_match.group(1) if role_match else ""
        is_bg = "bg" in role.lower()

        if is_bg:
            # Background vocals format - separate line
            split_background_vocals_index = re.search('<span ttm:role="x-bg"',string).span(0)[0]
            results.append(f"[{begin_time}]{agent}:{build_lrc_text(extract_spans_with_spaces(string[:split_background_vocals_index]))}<{end_time}>")
            results.append(f"[bg:{build_lrc_text(extract_spans_with_spaces(string[split_background_vocals_index:]))}]")
        else:
            # Regular vocals format
            agent = agent_match.group(1) if agent_match else "v1"
            lrc_line = f"[{begin_time}]{agent}:{text_content}<{end_time}>"
            results.append(lrc_line)

    return results

# Example usage
if __name__ == "__main__":
    test_strings = import_lyrics(sys.argv)

    converted = convert_to_lrc_format(test_strings)
    lyrics = ""
    for line in converted:
        lyrics += line + "\n"
    base_path = os.path.splitext(sys.argv[1])[0]
    output_path = f"{base_path}.elrc"
    save_lyrics(output_path, lyrics)

