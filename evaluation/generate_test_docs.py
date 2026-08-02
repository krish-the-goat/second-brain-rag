"""
Generates synthetic test documents (PDF) for the evaluation pipeline.
These cover Machine Learning, Python, and Distributed Systems topics
so that the test queries have retrievable ground truth.
"""

import os
from fpdf import FPDF

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_documents")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_pdf(filename: str, title: str, content_sections: list[tuple[str, str]]):
    """Create a simple PDF with titled sections."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(10)

    for heading, body in content_sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, heading, ln=True)
        pdf.set_font("Helvetica", "", 10)
        # Handle encoding by replacing problematic characters
        safe_body = body.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 5, safe_body)
        pdf.ln(5)

    pdf.output(os.path.join(OUTPUT_DIR, filename))
    print(f"  Created: {filename}")


def generate_ml_doc():
    sections = [
        (
            "What is Machine Learning?",
            "Machine learning is a subset of artificial intelligence that enables systems to learn "
            "from data and improve their performance without being explicitly programmed. It uses "
            "algorithms to identify patterns in data and make decisions with minimal human intervention.",
        ),
        (
            "Neural Networks",
            "A neural network consists of layers of interconnected neurons. Each neuron applies "
            "weights to inputs, sums them, and passes the result through an activation function. "
            "Networks with multiple hidden layers are called deep neural networks.",
        ),
        (
            "Supervised vs Unsupervised Learning",
            "Supervised learning uses labeled data for training, where the algorithm learns to map "
            "inputs to known outputs. Common tasks include classification and regression. "
            "Unsupervised learning works with unlabeled data, finding hidden patterns through "
            "techniques like clustering and dimensionality reduction.",
        ),
        (
            "Transfer Learning",
            "Transfer learning reuses a pretrained model on a new, related task. Instead of training "
            "from scratch, you fine-tune the pretrained model on your specific dataset. This is "
            "especially useful when you have limited training data.",
        ),
        (
            "Gradient Descent",
            "Gradient descent is an optimization algorithm used to minimize the loss function. "
            "It iteratively adjusts parameters in the direction of steepest descent. The learning "
            "rate controls the step size. Variants include SGD, Adam, and RMSprop.",
        ),
        (
            "Overfitting",
            "Overfitting occurs when a model learns the training data too well, including noise, "
            "and fails to generalize to unseen data. Signs include high training accuracy but low "
            "validation accuracy. Regularization, dropout, and cross-validation help prevent it.",
        ),
        (
            "Backpropagation",
            "Backpropagation computes gradients of the loss function with respect to each weight "
            "using the chain rule. It propagates error backward through the network layers, "
            "allowing efficient gradient computation for training deep networks.",
        ),
    ]
    create_pdf("machine_learning_fundamentals.pdf", "Machine Learning Fundamentals", sections)


def generate_python_doc():
    sections = [
        (
            "Python Data Structures",
            "Python's core data structures include: list (ordered, mutable sequences), "
            "dictionary (key-value pairs with O(1) lookup), tuple (immutable sequences), "
            "and set (unordered collections of unique elements).",
        ),
        (
            "Decorators",
            "Decorators are a way to modify or extend function behavior without changing the "
            "function itself. They use the @ syntax and are essentially higher-order functions "
            "that take a function as input and return a wrapper function with added behavior.",
        ),
        (
            "The Global Interpreter Lock (GIL)",
            "The GIL is a mutex in CPython that allows only one thread to execute Python bytecode "
            "at a time. This simplifies memory management but limits true parallel execution of "
            "threads. For CPU-bound work, multiprocessing is preferred over threading.",
        ),
        (
            "Async/Await and asyncio",
            "Python's asyncio provides a single-threaded event loop for concurrent I/O operations. "
            "Coroutines defined with async def are scheduled as tasks on the event loop. The await "
            "keyword suspends execution until the awaited coroutine completes, allowing other tasks "
            "to run in a non-blocking manner.",
        ),
        (
            "Garbage Collection",
            "Python uses reference counting as its primary memory management strategy. When an "
            "object's reference count drops to zero, it is immediately deallocated. A cycle "
            "detector handles circular references that reference counting alone cannot resolve.",
        ),
        (
            "REST vs GraphQL",
            "REST APIs expose multiple endpoints, one per resource. GraphQL provides a single "
            "endpoint with a typed schema where clients specify exactly what data they need in "
            "their query, eliminating over-fetching and under-fetching problems common in REST.",
        ),
    ]
    create_pdf("python_programming_guide.pdf", "Python Programming Guide", sections)


def generate_distributed_systems_doc():
    sections = [
        (
            "CAP Theorem",
            "The CAP theorem states that a distributed system can provide at most two of three "
            "guarantees simultaneously: Consistency (all nodes see the same data), Availability "
            "(every request receives a response), and Partition Tolerance (the system operates "
            "despite network partitions).",
        ),
        (
            "Eventual Consistency",
            "Eventual consistency is a consistency model where replicas may temporarily diverge "
            "but will converge to the same state given enough time without new updates. This "
            "trade-off enables higher availability in distributed databases.",
        ),
        (
            "Raft Consensus",
            "Raft is a consensus algorithm where nodes elect a leader that manages log replication. "
            "Followers replicate the leader's log entries. If the leader fails, a new election "
            "occurs among followers with the most up-to-date logs.",
        ),
        (
            "Microservices Architecture",
            "Microservices decompose applications into small, independent services that can be "
            "developed, deployed, and scaled independently. Services communicate via APIs, "
            "message queues, or event streams.",
        ),
        (
            "Knowledge Graphs",
            "A knowledge graph represents information as entities (nodes) connected by "
            "relationships (edges). This structure enables traversal queries that discover "
            "multi-hop connections between concepts.",
        ),
        (
            "Docker and Containerization",
            "Docker packages applications into lightweight, isolated containers that include "
            "all dependencies. Containers share the host OS kernel, making them more efficient "
            "than virtual machines. Images are built from Dockerfiles.",
        ),
    ]
    create_pdf("distributed_systems_overview.pdf", "Distributed Systems Overview", sections)


if __name__ == "__main__":
    print("Generating test documents...")
    generate_ml_doc()
    generate_python_doc()
    generate_distributed_systems_doc()
    print(f"\nDone! Documents saved to: {OUTPUT_DIR}")
