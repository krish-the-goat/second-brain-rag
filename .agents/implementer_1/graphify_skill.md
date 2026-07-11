---
name: graphify
description: Analyze the structural dependencies and knowledge graph of a project using the Graphify tool.
---

# Graphify Skill

You are equipped with the **Graphify** skill, allowing you to convert an entire project into an interactive, structured Knowledge Graph.

## When to use this skill
- When the user asks you to "use graphify", "analyze codebase structure", or "map the project".
- When you need a high-level overview of how different Python files, classes, and functions are connected, without reading all the raw text.
- When dealing with large repositories where grepping or reading files would exceed token limits.

## How to use this skill
1. Run the helper script located at `/Users/krishaggarwal/.gemini/config/skills/graphify/scripts/run_graphify.sh <TARGET_DIRECTORY>`.
2. This script will build the Knowledge Graph and output a summary.
3. If you need to read the raw graph data, the script generates a `graph.json` in the target directory which you can view using your `view_file` tool.
4. Use the relationships in the graph to understand architectural dependencies and answer the user's questions accurately.
