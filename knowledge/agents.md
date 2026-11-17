# Agent frameworks

## What an agent is

An agent is a language model that can choose to do things, not just say
things. You give it a set of tools, it decides which to call, it sees the
result, and it carries on until it has an answer.

The decision is the interesting part. Evaluating an agent means asking whether
it chose the right tool, which is a different question from whether its prose
was good.

## The frameworks

LangChain, LangGraph and CrewAI appear on job adverts constantly. They give
you the loop, the tool definitions, the memory and the plumbing so you do not
write it yourself.

They are worth knowing and they are not magic. Building one tool loop by hand
first is the fastest way to understand what the framework is doing for you.

## MCP

Model Context Protocol is an emerging standard for connecting a model to tools
and data sources. It is starting to appear in live job descriptions. Think of
it as a common plug shape so every tool does not need its own adapter.
