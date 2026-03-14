# OpenLearning

**AI-powered learning engineering platform. Identify skill gaps and generate personalized learning plans.**

Most learning platforms treat assessment as a static quiz. OpenLearning uses a [LangGraph](https://langchain-ai.github.io/langgraph/)-powered adaptive interview that calibrates to your level, targets specific Bloom taxonomy depths, and builds a knowledge graph in real time — then generates a personalized learning plan from the gaps it finds.

---

## Features

### Onboarding
Select a role to get started quickly, paste a job description to auto-extract skills, or browse and select manually from a curated taxonomy.

### Skill Assessment
Adaptive AI interview powered by Claude. The system calibrates difficulty with initial questions, then uses Bloom taxonomy levels to probe understanding depth across multiple topics.

### Gap Analysis
Radar chart visualization comparing your current proficiency against target levels, with priority-ranked gaps and actionable recommendations.

### Learning Plan
Phased, structured learning plan with theory, quiz, and lab modules — generated from your specific knowledge gaps.

---

## Quick Links

| Section | Description |
|---------|-------------|
| [Installation](getting-started/installation.md) | Prerequisites and setup instructions |
| [Quick Start](getting-started/quickstart.md) | Walk through your first assessment |
| [Architecture Overview](architecture/overview.md) | System design and component diagram |
| [Assessment Pipeline](architecture/assessment-pipeline.md) | Deep-dive into the LangGraph pipeline |
| [Knowledge Base Guide](guides/knowledge-base.md) | How to contribute domain knowledge |
| [API Reference](guides/api-reference.md) | Endpoint documentation |
| [Development Setup](development/setup.md) | Developer environment and Makefile commands |

---

## Contributing

We welcome contributions of all kinds. Knowledge base contributions (new domain YAML files) are especially valuable and don't require Python or TypeScript knowledge.

See [Contributing](https://github.com/onegunsamurai/OpenLearning/blob/main/CONTRIBUTING.md) for details.

## License

MIT License — see [LICENSE](https://github.com/onegunsamurai/OpenLearning/blob/main/LICENSE) for details.
