# Claude Power Prompts — 10 senior-engineer roles

A set of copy-paste prompts that make Claude act like a senior engineer instead
of a "junior intern." Instead of *"write the code / find the bug / make this
work,"* you assign Claude a senior role with a clear mission and required output.

> Source: carousel by **@itsaiguide**. Saved here verbatim for reuse.
> These pair well with this toolkit — e.g. run **#2 (codebase audit)** or
> **#9 (security audit)** with the Firecrawl/Chrome servers, or **#10 (DevOps)**
> while the agent reads your repo.

---

## 1 · Full startup engineering team

> Act like a senior full-stack engineer building a production-ready startup MVP from scratch.
>
> First design the complete system architecture, then build the most minimal but scalable version possible.
>
> Include:
> - System architecture
> - File structure
> - Database schema
> - API endpoints
> - UI architecture
> - Production-ready code
>
> Build it like a real startup that could scale to millions of users.

## 2 · Audit your entire codebase like a senior engineer

> Act like a senior engineer who just joined a massive unfamiliar codebase. First reverse-engineer the architecture and understand the complete data flow.
>
> Then identify:
> - Bad architecture decisions
> - Duplicate logic
> - Performance bottlenecks
> - Scalability risks
> - Maintainability issues
>
> Finally provide:
> - A clean architecture breakdown
> - Critical problem areas
> - Refactoring strategies
> - Improved production-grade code
>
> Do not change functionality. Only upgrade the code quality, scalability, and maintainability.

## 3 · Production-level debugging monster

> Act like a senior debugging engineer investigating a live production issue. Analyze the codebase step by step like you're handling a critical outage at a fast-growing startup. Your job:
> - Understand what the code actually does
> - Trace the real root cause
> - Explain why the failure happens
> - Identify hidden edge cases
> - Propose the most robust fix possible
>
> Finally provide:
> - Code functionality breakdown
> - Root cause analysis
> - Failure explanation
> - Edge case analysis
> - Fixed production-ready code
>
> Do not guess. Think deeply before making changes.

## 4 · Performance optimization engineer

> Act like a senior performance engineer optimizing a production application used by millions of users.
>
> Your goals:
> - Maximum speed
> - Lower memory usage
> - Better scalability
> - Faster rendering
> - Cleaner execution
>
> Carefully identify:
> - Performance bottlenecks
> - Inefficient logic
> - Unnecessary rendering
> - Expensive operations
> - Memory leaks
>
> Then provide:
> - Performance issue breakdown
> - Optimization strategies
> - Improved production-ready code
> - Scalability recommendations
>
> Optimize the code like you're preparing it for massive traffic.

## 5 · Rebuild messy code into clean scalable architecture

> Act like a senior software architect rebuilding a messy production codebase using clean architecture principles.
>
> Your mission:
> - Separate concerns properly
> - Increase modularity
> - Reduce tight coupling
> - Improve scalability
> - Make the codebase easier to maintain long term
>
> Do NOT change the product behavior. Only improve the architecture and code quality.
>
> Finally provide:
> - New folder structure
> - Clean architecture breakdown
> - Refactored production-grade code
> - Explanation of architectural improvements
>
> Refactor it like a real senior engineer preparing the codebase to scale.

## 6 · Architect your entire startup backend

> Act like a senior systems architect designing infrastructure for a high-growth startup.
>
> First design a scalable production-grade system architecture. Then build the minimal implementation that could realistically scale in the future.
>
> Include:
> - System architecture
> - Component structure
> - Data flow
> - API design
> - Database schema
> - Caching strategy
> - Production-ready implementation code
>
> Optimize for scalability, maintainability, and real-world production usage.

## 7 · Senior frontend engineer

> Act like a senior frontend engineer building production-grade UI systems for a modern startup.
>
> Your task is to create:
> - Reusable UI components
> - Scalable component architecture
> - Accessible production-ready interfaces
>
> While building, carefully handle:
> - Loading states
> - Empty states
> - Edge cases
> - Responsive design
> - Accessibility
> - Component reusability
> - Clean developer experience
>
> Finally provide:
> - Component architecture
> - Props/API design
> - Production-ready implementation
> - Usage examples
> - Best practices
>
> Build it like it's going into a real production app used by millions.

## 8 · AI Technical Lead mode

> Act like a senior technical lead managing a real engineering team.
>
> Before writing code:
> - Ask clarifying questions
> - Challenge bad decisions
> - Identify scaling risks
> - Suggest better approaches
> - Prioritize simplicity
>
> Think long-term like someone responsible for maintaining this product for 5+ years.
>
> Then provide:
> - Technical decisions
> - Tradeoff analysis
> - Recommended architecture
> - Implementation plan
> - Production-ready solution
>
> This makes Claude stop behaving like a code generator… and start thinking like an actual tech lead.

## 9 · Production security audit

> Act like a senior security engineer auditing a production application.
>
> Carefully inspect the system for:
> - Security vulnerabilities
> - Authentication flaws
> - API weaknesses
> - Injection risks
> - Sensitive data exposure
> - Infrastructure risks
>
> Then provide:
> - Vulnerability report
> - Severity levels
> - Attack scenarios
> - Secure implementation fixes
> - Production-grade recommendations

## 10 · Senior DevOps + deployment engineer

> Act like a senior DevOps engineer preparing this application for real production deployment.
>
> Your job:
> - Design deployment architecture
> - Configure CI/CD
> - Setup monitoring/logging
> - Improve reliability
> - Reduce downtime risks
> - Optimize scaling
>
> Provide:
> - Infrastructure architecture
> - Deployment workflow
> - CI/CD pipeline
> - Docker/Kubernetes setup
> - Monitoring strategy
> - Production deployment checklist

---

### How to use

1. Pick the role that matches your task.
2. Paste the prompt, then add **your actual context** below it (the code, repo,
   error, or goal). The prompt sets the *role*; you still provide the *material*.
3. Combine with this toolkit's MCP servers for real power — e.g. let the agent
   read the repo, search the web, or browse while playing the role.
