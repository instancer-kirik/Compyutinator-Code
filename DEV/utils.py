# utils.py
import re
import difflib

def extract_code_blocks(text, key_symbols=None):
    blocks = {}
    lines = text.split('\n')
    current_block = []
    current_key = 'global'
    start_line = 0

    for i, line in enumerate(lines):
        if key_symbols and line.strip().startswith(tuple(key_symbols)):
            if current_block:
                blocks[current_key] = {
                    'content': '\n'.join(current_block),
                    'start_line': start_line,
                    'end_line': i - 1
                }
            current_key = line.strip()
            current_block = [line]
            start_line = i
        else:
            current_block.append(line)

    if current_block:
        blocks[current_key] = {
            'content': '\n'.join(current_block),
            'start_line': start_line,
            'end_line': len(lines) - 1
        }
    return blocks

def extract_diff_blocks(text):
    diff_blocks = []
    lines = text.split('\n')
    current_block = []

    for line in lines:
        if line.startswith(('+ ', '- ')):
            current_block.append(line)
        elif current_block:
            diff_blocks.append(current_block)
            current_block = []

    if current_block:
        diff_blocks.append(current_block)

    return diff_blocks

def apply_diff_to_content(content, diff_blocks):
    lines = content.split('\n')
    for block in diff_blocks:
        for line in block:
            if line.startswith('+'):
                match = re.match(r'\+(\d+):', line)
                if match:
                    line_num = int(match.group(1)) - 1
                    new_line = line[len(match.group(0)):].strip()
                    lines.insert(line_num, new_line)
            elif line.startswith('-'):
                match = re.match(r'-(\d+):', line)
                if match:
                    line_num = int(match.group(1)) - 1
                    if 0 <= line_num < len(lines):
                        del lines[line_num]

    return '\n'.join(lines)

def compute_diff(original_text, new_text):
    return list(difflib.ndiff(original_text.splitlines(True), new_text.splitlines(True)))