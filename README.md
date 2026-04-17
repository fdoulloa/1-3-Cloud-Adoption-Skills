# Huawei Cloud Adoption Skills

## Purpose

This repository defines a practical skill framework for Huawei Cloud adoption work.

Here, an AI skill is not just the ability to write prompts. It is a reusable capability unit built around a cloud scenario, where AI is used to support understanding, design, migration, operations, development, analysis, or optimization.

Each AI skill should include five elements:

- Scenario: what business problem or cloud scenario it addresses
- Knowledge: what cloud products, architecture, and domain logic are required
- Tools: what AI models, APIs, scripts, platforms, or workflows are used
- Method: how AI is embedded into the delivery process
- Output and validation: what is produced and how the result is verified

## Design Principles

This framework follows five core principles:

1. Start from cloud scenarios, then map AI capabilities.
2. Every skill must connect to a real use case.
3. Every skill must become a reusable asset.
4. Every skill must have a maturity level.
5. Every skill must be measurable against business outcomes.

The goal is to organize skills by business value, cloud scenario, and delivery action, instead of organizing them only by model techniques such as prompting, RAG, agents, or fine-tuning.

## General Skills

General Skills are the common foundation required across all Huawei Cloud adoption work. They are not limited to one cloud service, one project type, or one delivery team.

## Level 1 Domains

The first level of the framework follows the established `1+3` domain structure. These domains will host different skill sets as the repository grows:

- [Cloud Foundation](./Cloud-Foundation/README.md)
- [Application Modernization](./Application-Modernization/README.md)
- [Big Data](./Big-Data/README.md)
- [AI](./AI/README.md)

The General Skills defined in this document apply across all four Level 1 domains.

## Level 2 Use Cases

Under each Level 1 domain, the framework is further organized by Level 2 use cases. This is the layer where skills are grouped by delivery scenarios such as landing zones, migration, data governance, agent platforms, or AI-ready data foundations.

Each Level 1 domain contains its own Level 2 use case directories and English descriptions:

- [Cloud Foundation](./Cloud-Foundation/README.md)
- [Application Modernization](./Application-Modernization/README.md)
- [Big Data](./Big-Data/README.md)
- [AI](./AI/README.md)

### G1. Scenario Understanding and Requirement Abstraction

Translate customer requirements into a structured view of the current system, process pain points, possible AI intervention points, and the expected pull on cloud resource consumption.

### G2. AI Interaction and Prompt Design

Use AI effectively through structured questioning, output control, multi-turn clarification, role setting, constraint injection, and result verification.

### G3. Cloud Knowledge Retrieval and Knowledge Injection

Improve AI usefulness by connecting it with product documents, architecture knowledge, solution materials, FAQs, SOPs, and project experience through retrieval and knowledge update mechanisms.

### G4. API / SDK / CLI / IaC Automation

Move beyond answers into actions by using APIs, SDKs, CLI tools, Terraform, IaC patterns, and AI-assisted script generation and correction.

### G5. Security and Governance

Keep skill execution safe and controllable through identity and permission management, sensitive data protection, auditability, output control, model usage boundaries, and compliance awareness.

### G6. Observability, Evaluation, and Optimization

Measure and improve skills through accuracy, success rate, latency, cost, token consumption, task completion rate, and human replacement efficiency.

### G7. Integration and Workflow Orchestration

Embed AI into delivery workflows by connecting it with IDEs, DevOps pipelines, ticketing systems, monitoring systems, data platforms, and agent or workflow orchestration patterns.

### G8. Assetization and Replication

Turn every skill into repeatable assets such as Skill Cards, demo scripts, SOPs, training content, PoC templates, and replication templates.

## Skill Levels

Each skill should have a clear maturity level:

- Level 1. Understand: explain the scenario, required knowledge, and expected outputs
- Level 2. Execute: apply the skill in a real delivery task with repeatable steps
- Level 3. Replicate: package the skill into reusable assets that can be copied across projects

The level should reflect delivery capability, not just awareness or training attendance.

## Required Skill Assets

Each skill should eventually be documented and packaged into reusable outputs:

- Solution material
- Demo
- Scripts
- Best practices
- Test report
- FAQ and troubleshooting
- Reusable template

## Business Value Alignment

The framework is intended to support:

- Top project breakthrough
- PoC success
- Commercial replication
- Revenue growth
- Asset accumulation

This repository starts with the general framework. Future additions can extend the structure into domain-specific and use-case-specific Huawei Cloud Adoption Skills.
