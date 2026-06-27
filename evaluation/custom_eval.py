import asyncio
import json
import os
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure API keys are loaded
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")

from app.rag.pipeline import RAGPipeline
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

console = Console()

async def evaluate():
    console.print(Panel.fit("[bold blue]Custom LLM-as-a-Judge Evaluation[/bold blue]", border_style="blue"))
    
    with open("evaluation/test_queries.json", "r") as f:
        queries = json.load(f)
        
    pipeline = RAGPipeline()
    judge_llm = ChatGoogleGenerativeAI(model="models/gemini-2.0-flash", convert_system_message_to_human=True)
    
    total_queries = len(queries)
    results = []
    
    console.print(f"Running evaluation on {total_queries} queries...\n")
    
    for i, item in enumerate(queries):
        question = item["question"]
        ground_truth = item["ground_truth_answer"]
        expected_source = item["expected_source_filename"]
        
        console.print(f"[cyan]Q{i+1}:[/cyan] {question}")
        
        # 1. Run RAG Pipeline
        try:
            rag_res = await pipeline.ask(question)
            answer = rag_res["answer"]
            citations = rag_res["citations"]
            console.print(f"[yellow]Retrieved {len(citations)} citations:[/yellow]")
            for c in citations:
                console.print(f"  - {c.get('filename')}")
        except Exception as e:
            console.print(f"[red]Error processing query:[/red] {e}")
            continue
            
        # 2. Check Context Recall
        retrieved_files = [c["filename"] for c in citations]
        if expected_source is None:
            context_score = 1.0 if not retrieved_files else 0.0
        else:
            context_score = 1.0 if expected_source in retrieved_files else 0.0
            
        # 3. LLM-as-a-Judge for Accuracy
        judge_prompt = f"""
        You are an expert evaluator. Compare the GENERATED ANSWER to the GROUND TRUTH for the given QUESTION.
        Determine if the generated answer is factually correct and semantically equivalent to the ground truth.
        Output ONLY a JSON object with a single key "accuracy_score" set to 1 if correct, and 0 if incorrect.
        
        QUESTION: {question}
        GROUND TRUTH: {ground_truth}
        GENERATED ANSWER: {answer}
        """
        
        try:
            if os.getenv("MOCK_LLM", "false").lower() == "true":
                accuracy_score = 1.0 if context_score == 1.0 else 0.0
            else:
                judge_res = await judge_llm.ainvoke([HumanMessage(content=judge_prompt)])
                output = judge_res.content.replace("```json", "").replace("```", "").strip()
                score_data = json.loads(output)
                accuracy_score = float(score_data.get("accuracy_score", 0))
        except Exception as e:
            accuracy_score = 0.0
            
        results.append({
            "type": item["type"],
            "accuracy": accuracy_score,
            "context_recall": context_score
        })
        
    # Calculate metrics
    avg_accuracy = sum(r["accuracy"] for r in results) / total_queries
    avg_recall = sum(r["context_recall"] for r in results) / total_queries
    
    table = Table(title="Final Evaluation Metrics")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Score", style="magenta")
    
    table.add_row("Answer Accuracy (LLM Judge)", f"{avg_accuracy * 100:.1f}%")
    table.add_row("Context Recall (Source Match)", f"{avg_recall * 100:.1f}%")
    
    console.print("\n")
    console.print(table)
    
    if avg_accuracy < 0.8 or avg_recall < 0.7:
        console.print("\n[bold red]Evaluation failed threshold requirements![/bold red]")
        exit(1)
    else:
        console.print("\n[bold green]Evaluation passed all requirements![/bold green]")
        
if __name__ == "__main__":
    asyncio.run(evaluate())
