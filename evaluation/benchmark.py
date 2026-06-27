import os
import sys
import asyncio
import numpy as np
from rich.console import Console
from rich.table import Table

# Add backend to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
from app.rag.pipeline import RAGPipeline

console = Console()

async def run_benchmark():
    pipeline = RAGPipeline()
    
    num_queries = 2
    console.print(f"[bold yellow]Running {num_queries} queries for benchmark...[/bold yellow]")
    
    embedding_times = []
    retrieval_times = []
    generation_times = []
    total_times = []
    
    for i in range(num_queries):
        question = f"What is the significance of the data point {i} in the context?"
        res = await pipeline.ask(question)
        
        timings = res.get("timings", {})
        embedding_times.append(timings.get("embedding_ms", 0))
        retrieval_times.append(timings.get("retrieval_ms", 0))
        generation_times.append(timings.get("generation_ms", 0))
        total_times.append(timings.get("total_ms", 0))
        
    def get_percentiles(data):
        return {
            "p50": np.percentile(data, 50),
            "p95": np.percentile(data, 95),
            "p99": np.percentile(data, 99)
        }
        
    emb_stats = get_percentiles(embedding_times)
    ret_stats = get_percentiles(retrieval_times)
    gen_stats = get_percentiles(generation_times)
    tot_stats = get_percentiles(total_times)
    
    table = Table(title=f"Benchmark Results ({num_queries} queries) in ms")
    table.add_column("Phase", style="cyan")
    table.add_column("P50", justify="right")
    table.add_column("P95", justify="right")
    table.add_column("P99", justify="right")
    
    table.add_row("Embedding", f"{emb_stats['p50']:.1f}", f"{emb_stats['p95']:.1f}", f"{emb_stats['p99']:.1f}")
    table.add_row("Retrieval", f"{ret_stats['p50']:.1f}", f"{ret_stats['p95']:.1f}", f"{ret_stats['p99']:.1f}")
    table.add_row("Generation", f"{gen_stats['p50']:.1f}", f"{gen_stats['p95']:.1f}", f"{gen_stats['p99']:.1f}")
    table.add_row("Total E2E", f"{tot_stats['p50']:.1f}", f"{tot_stats['p95']:.1f}", f"{tot_stats['p99']:.1f}", style="bold green")
    
    console.print(table)
    
    if tot_stats['p95'] > 10000:
        console.print("[bold red]WARNING: P95 end-to-end latency exceeds 10 seconds! (10000ms)[/bold red]")
    else:
        console.print("[bold green]Performance is within acceptable limits (< 10s P95).[/bold green]")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
