## 2026-07-06T14:20:25Z
<USER_REQUEST>
You are a worker agent analyzing and documenting the codebase: second-brain-rag located at /Users/krishaggarwal/Desktop/second-brain-rag.

YOUR OBJECTIVE:
1. Run the graphify script at `/Users/krishaggarwal/.gemini/config/skills/graphify/scripts/run_graphify.sh` on the project directory `/Users/krishaggarwal/Desktop/second-brain-rag`.
2. Read and analyze the generated `graph.json` file in the project directory, as well as the source files, directories, configuration files (e.g. backend/frontend configs) to understand the project structure, design patterns, and architecture.
3. Write a comprehensive markdown documentation file to: `/Users/krishaggarwal/teamwork_projects/portfolio_codebase_analysis/docs/second-brain-rag_doc.md`
The documentation MUST contain:
- # Architecture: Overview of the codebase layout, main components, module boundaries, design patterns, and high-level structure.
- # Tech Stack: Detailed list of programming languages, frameworks, libraries, database systems, and dev tools used.
- # Data Flow: A detailed end-to-end trace of at least one critical flow (e.g., from an API endpoint, controller, or script entry down to storage, file, or database).
- # Structural Mapping (Graphify): A section summarizing the findings from the graphify tool (number of nodes/edges, key dependency clusters, and structural insights from graph.json).
- Reference the path of the generated `graph.json` file.

SCOPE BOUNDARIES:
- Do NOT modify any existing source code or files within the project.
- Do NOT create any source code or script files.
- ONLY write the documentation file at `/Users/krishaggarwal/teamwork_projects/portfolio_codebase_analysis/docs/second-brain-rag_doc.md`.

COMPLETION CRITERIA:
- The `graphify` script runs and generates `graph.json` (or logs error/alternative if failed).
- The file `/Users/krishaggarwal/teamwork_projects/portfolio_codebase_analysis/docs/second-brain-rag_doc.md` is successfully written.
- The document has all required sections (Architecture, Tech Stack, Data Flow, Structural Mapping) and traces a real end-to-end flow.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please report back when done with the path to the written documentation and a summary of your findings.
</USER_REQUEST>
