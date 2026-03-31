// hooks/post-commit-doc-check.js
// PostToolUse hook — after a successful git commit, reminds to check doc sync
// Lightweight: just checks if any doc-adjacent files were changed

const input = JSON.parse(process.argv[2] || '{}');
const command = input?.tool_input?.command || '';

// Only trigger after git commit
if (!command.match(/git\s+commit/)) {
  process.exit(0);
}

const { execSync } = require('child_process');

try {
  // Check what files were in the last commit
  const files = execSync('git diff --name-only HEAD~1 HEAD 2>/dev/null', { encoding: 'utf8' });

  // Detect if code files changed but no docs changed
  const codeChanged = files.split('\n').some(f =>
    f.match(/\.(ts|tsx|js|jsx|py|go|rs|java|kt)$/) && !f.includes('.test.') && !f.includes('.spec.')
  );
  const docsChanged = files.split('\n').some(f =>
    f.match(/\.(md|mdx)$/) || f.includes('docs/') || f.includes('CHANGELOG')
  );

  if (codeChanged && !docsChanged) {
    console.log(JSON.stringify({
      notification: '⚠️ Code changed but no docs updated. Consider running /doc-sync to check documentation freshness.'
    }));
  }
} catch (e) {
  // Silent fail — don't break workflow
}
