import sys
import os
import time
from app.llm_client import LLMClient

def read_topics_from_files(file_paths):
    topics = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                topic: str = f.read()
                topics.append(topic)
        else:
            print(f"Warning: File {file_path} not found.")
    return topics

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_llm_client.py <topic_file1> [<topic_file2> ...]")
        sys.exit(1)
    
    topics = read_topics_from_files(sys.argv[1:])
    if not topics:
        print("No topics found in provided files.")
        sys.exit(1)
    
    print(f"Starting LLM Client test with {len(topics)} topics...")
    job_id = "test_run_" + str(int(time.time()))
    client = LLMClient()
    dialogue = client.generate_podcast_script(topics, job_id)
    
    print("Generated Podcast Dialogue:")
    for i, entry in enumerate(dialogue):
        print(f"{i+1}. [{entry['speaker']}] {entry['text']}")