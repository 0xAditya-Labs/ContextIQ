import os
from .rag_chain import ask_question
from .vectorstore import prepare_and_store_documents

def run_tests():
    questions = [
        "How do I fix error 809 when connecting to the VPN?",
        "I dropped my laptop and the screen cracked. What should I do?",
        "I need a license for a data visualization dashboard tool for my whole team. How do I request it?",
        "Why is my timesheet submit button greyed out?"
    ]

    strategies = ["metadata_chunk", "parent_document"]

    print("=" * 80)
    print("STRATEGY COMPARISON TEST")
    print("=" * 80)
    
    # Optional: We could run prepare_and_store_documents() here to ensure the vectorstore is populated
    # with the correct metadata, but assuming it has already been run once, we don't strictly need to.
    # However, since we just changed the schema (added ticket_id to chunk metadata), let's re-run it 
    # to ensure the DB is perfectly up to date.
    print("\n--- Initializing / Updating Vectorstore ---")
    prepare_and_store_documents()
    print("-" * 43)

    for i, question in enumerate(questions, 1):
        print(f"\n\nQUESTION {i}: {question}")
        print("-" * 80)
        
        for strategy in strategies:
            print(f"\n[{strategy.upper()} STRATEGY]")
            result = ask_question(question, strategy_name=strategy)
            
            print(f"SOURCES: {', '.join(result['sources']) if result['sources'] else 'None'}")
            print(f"ANSWER:  {result['answer']}")
            print("-" * 40)
            
    print("\n\nTest complete!")

if __name__ == "__main__":
    run_tests()
