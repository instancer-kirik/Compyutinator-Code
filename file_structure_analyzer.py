import os
import argparse
from datetime import datetime
import hashlib
import json

def get_file_info(path):
    stats = os.stat(path)
    return {
        "last_modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "size": stats.st_size,
        "type": "file" if os.path.isfile(path) else "directory"
    }

def generate_file_structure(start_path, ignore_dirs=None, ignore_files=None, sort_by_modified=False):
    if ignore_dirs is None:
        ignore_dirs = ['.git', '__pycache__', 'venv', 'env']
    if ignore_files is None:
        ignore_files = ['.gitignore', '.DS_Store']

    structure = []

    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, '').count(os.sep)
        indent = '  ' * level
        folder_name = os.path.basename(root)

        if folder_name in ignore_dirs:
            continue

        folder_info = get_file_info(root)
        structure.append({
            "path": f"{indent}{folder_name}/",
            "info": folder_info
        })

        sub_indent = '  ' * (level + 1)
        for file in files:
            if file not in ignore_files:
                file_path = os.path.join(root, file)
                file_info = get_file_info(file_path)
                structure.append({
                    "path": f"{sub_indent}{file}",
                    "info": file_info
                })

        dirs[:] = [d for d in dirs if d not in ignore_dirs]

    if sort_by_modified:
        structure.sort(key=lambda x: x["info"]["last_modified"], reverse=True)

    return structure

def tokenize_for_ai(structure):
    tokens = []
    for item in structure:
        path_parts = item["path"].strip().split('/')
        tokens.extend(path_parts)
        tokens.append(item["info"]["type"])
        tokens.append(item["info"]["last_modified"])
        tokens.append(str(item["info"]["size"]))
    return tokens

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a file structure outline.")
    parser.add_argument("path", help="The path to the directory you want to analyze.")
    parser.add_argument("--sort", action="store_true", help="Sort by last modified date.")
    parser.add_argument("--output", choices=["text", "json", "tokens"], default="text", help="Output format")
    args = parser.parse_args()

    structure = generate_file_structure(args.path, sort_by_modified=args.sort)

    if args.output == "text":
        for item in structure:
            print(f"{item['path']} (Last modified: {item['info']['last_modified']}, Size: {item['info']['size']} bytes)")
    elif args.output == "json":
        print(json.dumps(structure, indent=2))
    elif args.output == "tokens":
        tokens = tokenize_for_ai(structure)
        print(json.dumps(tokens))