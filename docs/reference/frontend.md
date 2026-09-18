# Frontend

## Streamlit application

::: src.chatbot_ui.main

The retrieval selector exposes Vanilla, Hybrid and Agentic modes. Changing corpus, mode or
answer model starts an isolated frontend/backend conversation. Agentic answers include a
collapsed execution summary with plan, outcome and bounded retrieval statistics; raw prompts,
evidence text and hidden reasoning are intentionally not rendered.

## HTML templates

::: src.chatbot_ui.htmlTemplates
