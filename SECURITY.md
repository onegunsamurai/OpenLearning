# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in OpenLearning, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email: **security@openlearning.dev** (or open a private security advisory via GitHub).

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix and disclosure**: Coordinated with reporter

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Security Practices

- API keys are managed via environment variables, never committed to source
- CI pipeline includes Gitleaks secret scanning
- CodeQL analysis runs weekly for Python and JavaScript/TypeScript
- Dependabot monitors dependencies for known vulnerabilities
