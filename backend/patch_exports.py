import sys

with open("../analysis.py", "r") as f:
    lines = f.readlines()

# Extract descriptive_stats (lines 704 to 1008 - indices 704:1008)
desc_stats = lines[704:1008]

with open("analyzer.py", "r") as f:
    analyzer = f.readlines()

# Find def build_excel_files
insert_idx = -1
for i, line in enumerate(analyzer):
    if line.startswith("def build_excel_files("):
        insert_idx = i
        break

# Inject descriptive_stats
new_analyzer = analyzer[:insert_idx] + ["\n"] + desc_stats + ["\n"] + analyzer[insert_idx:]

with open("analyzer.py", "w") as f:
    f.writelines(new_analyzer)

print("Injected descriptive_stats successfully.")
