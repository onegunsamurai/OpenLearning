// hooks/pre-commit-gate.js
// PreToolUse hook — prevents git commit if quality gate hasn't been run
// Add to hooks.json: PreToolUse on Bash when command contains "git commit"

const fs = require('fs');
const path = require('path');

const input = JSON.parse(process.argv[2] || '{}');
const command = input?.tool_input?.command || '';

// Only gate git commit commands
if (!command.match(/git\s+commit/)) {
  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

// Block --no-verify
if (command.includes('--no-verify') || command.includes('-n')) {
  console.log(JSON.stringify({
    decision: 'block',
    reason: 'Pipeline rule: --no-verify is not allowed. Quality gates must pass before commit.'
  }));
  process.exit(0);
}

// Check if quality gate was run (look for recent gate report)
const gateReportPath = path.join(process.cwd(), '.pipeline', 'last-gate-report.json');
try {
  if (fs.existsSync(gateReportPath)) {
    const report = JSON.parse(fs.readFileSync(gateReportPath, 'utf8'));
    const ageMs = Date.now() - new Date(report.timestamp).getTime();
    const maxAgeMs = 10 * 60 * 1000; // 10 minutes

    if (ageMs > maxAgeMs) {
      console.log(JSON.stringify({
        decision: 'block',
        reason: `Quality gate report is ${Math.round(ageMs / 60000)} minutes old. Run /quality-gate before committing.`
      }));
      process.exit(0);
    }

    if (report.status === 'FAIL') {
      console.log(JSON.stringify({
        decision: 'block',
        reason: `Quality gate FAILED with ${report.critical} critical and ${report.high} high issues. Fix issues and re-run /quality-gate.`
      }));
      process.exit(0);
    }
  }
} catch (e) {
  // If we can't read the report, allow commit (don't break workflow on hook errors)
}

console.log(JSON.stringify({ decision: 'allow' }));
