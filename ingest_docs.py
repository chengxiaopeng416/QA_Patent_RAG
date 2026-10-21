import os, sys

from qa_rag_agent.document_utils import load_document, split_document
from qa_rag_agent.rag_tools import retrieve_vector_store

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


base = os.path.join(os.path.dirname(__file__), "docs")
print(f"docs path: {base}")
print(f"exists: {os.path.isdir(base)}")
for f in os.listdir(base):
    print(f"  {f} -> .{f.rsplit('.',1)[-1].lower()}")

docs = load_document(base)
print(f"loaded docs: {len(docs)}")

chunks = split_document(docs)
print(f"chunks: {len(chunks)}")

if chunks:
    retrieve_vector_store.add_documents(chunks)
    print(f"done: {len(chunks)} chunks ingested")
else:
    print("no chunks to ingest")
