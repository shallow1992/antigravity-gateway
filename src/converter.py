"""Markdown converter from GitHub Flavored Markdown (GFM) to Slack mrkdwn."""

import re
from typing import List

# Regex patterns for code blocks and inline code protection
FENCED_CODE_BLOCK_PATTERN = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"(`[^`\n]+`)")

# Markdown syntax patterns
HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
STRIKETHROUGH_PATTERN = re.compile(r"~~(.+?)~~")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Max characters per Slack message block to avoid truncation
MAX_SLACK_BLOCK_LENGTH = 3000


def convert_gfm_to_slack_mrkdwn(text: str) -> str:
    """Convert standard GitHub Flavored Markdown to Slack mrkdwn format."""
    if not text:
        return text

    # Step 1: Protect fenced code blocks (```...```) from formatting transformations
    code_blocks: List[str] = []

    def _preserve_code_block(match: re.Match) -> str:
        idx = len(code_blocks)
        code_blocks.append(match.group(1))
        return f"@@GATEWAY_CODE_BLOCK_{idx}@@"

    protected_text = FENCED_CODE_BLOCK_PATTERN.sub(_preserve_code_block, text)

    # Step 2: Protect inline code (`...`)
    inline_codes: List[str] = []

    def _preserve_inline_code(match: re.Match) -> str:
        idx = len(inline_codes)
        inline_codes.append(match.group(1))
        return f"@@GATEWAY_INLINE_CODE_{idx}@@"

    protected_text = INLINE_CODE_PATTERN.sub(_preserve_inline_code, protected_text)

    # Step 3: Convert Tables to fixed-width code blocks
    def _convert_tables(content: str) -> str:
        lines = content.split("\n")
        output_lines: List[str] = []
        table_buffer: List[str] = []

        for line in lines:
            if line.strip().startswith("|") and line.strip().endswith("|"):
                table_buffer.append(line)
            else:
                if table_buffer:
                    output_lines.append("```")
                    output_lines.extend(table_buffer)
                    output_lines.append("```")
                    table_buffer = []
                output_lines.append(line)

        if table_buffer:
            output_lines.append("```")
            output_lines.extend(table_buffer)
            output_lines.append("```")

        return "\n".join(output_lines)

    converted = _convert_tables(protected_text)

    # Step 4: Convert Headers (# Header -> *Header*)
    converted = HEADER_PATTERN.sub(r"*\2*", converted)

    # Step 5: Convert Bold (**text** -> *text*, __text__ -> *text*)
    converted = BOLD_PATTERN.sub(lambda m: f"*{m.group(1) or m.group(2)}*", converted)

    # Step 6: Convert Strikethrough (~~text~~ -> ~text~)
    converted = STRIKETHROUGH_PATTERN.sub(r"~\1~", converted)

    # Step 7: Convert Links ([title](url) -> <url|title>)
    converted = LINK_PATTERN.sub(r"<\2|\1>", converted)

    # Step 8: Restore Inline Codes
    for idx, inline_code in enumerate(inline_codes):
        converted = converted.replace(f"@@GATEWAY_INLINE_CODE_{idx}@@", inline_code)

    # Step 9: Restore Fenced Code Blocks
    for idx, code_block in enumerate(code_blocks):
        converted = converted.replace(f"@@GATEWAY_CODE_BLOCK_{idx}@@", code_block)

    return converted


def split_message_for_slack(text: str, max_length: int = MAX_SLACK_BLOCK_LENGTH) -> List[str]:
    """Split a long text into chunks that fit comfortably within Slack message limits."""
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    lines = text.split("\n")
    current_chunk: List[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_length and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
