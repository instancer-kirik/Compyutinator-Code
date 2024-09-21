import os
import ast
import sys
from collections import defaultdict

def find_imports(directory):
    imports = defaultdict(set)
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for n in node.names:
                                    imports[n.name.split('.')[0]].add(file)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports[node.module.split('.')[0]].add(file)
                    except Exception as e:
                        print(f"Error parsing {file}: {e}")
    return imports

# Use the current directory, or specify your project directory
project_directory = '.' if len(sys.argv) < 2 else sys.argv[1]
project_imports = find_imports(project_directory)

print("Project imports:")
for imp, files in sorted(project_imports.items()):
    print(f"{imp}: used in {', '.join(files)}")
    
    
    
    