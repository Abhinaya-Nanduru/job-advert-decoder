# RAG and vector databases

## What RAG means

RAG stands for retrieval augmented generation. The model does not know about
your documents. RAG is the step where you find the relevant bits of your own
material first, and put them in front of the model before you ask the question.

Without it the model answers from whatever it absorbed during training, which
for anything about your company is nothing at all.

## The five steps

Chunk, embed, store, retrieve, answer. You cut documents into passages, turn
each passage into numbers that capture its meaning, keep those numbers
somewhere you can search, find the closest ones to the question, and hand them
to the model.

## Vector databases

A vector database is the store in the middle of that. It holds the numbers and
answers the question "which passages are closest to this one". Names you will
see on job adverts include Pinecone, Weaviate, Chroma and pgvector.

For a small set of documents you do not need one. Plain arithmetic over a few
hundred passages is fast enough, and starting there teaches you what the
database is actually doing for you.
