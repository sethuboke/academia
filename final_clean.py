import os
import shutil
import subprocess

# Clean up temp files
d = 'c:/Users/PC/academia'
for f in os.listdir(d):
    if f.startswith(('check_', 'commit_', 'diff_', 'list_git', 'clean_and', 'clean_more')) or f == 'nul':
        p = os.path.join(d, f)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif f != 'nul':
            os.remove(p)

# Commit any remaining changes
result = subprocess.run(['git', 'add', '-A'], cwd=d, capture_output=True, text=True)
print('git add -A:', result.stdout, result.stderr)

result = subprocess.run(['git', 'commit', '-m', 'Clean temp files'], cwd=d, capture_output=True, text=True)
print('git commit:', result.stdout, result.stderr)

# Final git status
result = subprocess.run(['git', 'status', '--porcelain'], cwd=d, capture_output=True, text=True)
print('\\nFinal git status:')
print(result.stdout if result.stdout else 'Working tree clean')
