from pydantic import BaseModel, Field
from typing import List, Dict, Any, Annotated, Optional
from operator import add

from api.rag.agent import ToolCall, RAGUsedContext, agent_node
from api.rag.utils.utils import get_tool_descriptions_from_node
from api.rag.tools import get_formatted_context
from api.core.config import config

from qdrant_client import QdrantClient

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver


class State(BaseModel):
    messages: Annotated[List[Any], add] = []
    answer: str = ""
    iteration: int = Field(default=0)
    final_answer: bool = Field(default=False)
    available_tools: List[Dict[str, Any]] = []
    tool_calls: Optional[List[ToolCall]] = Field(default_factory=list)
    retrieved_context_ids: List[RAGUsedContext] = []


def tool_router(state: State) -> str:
    """Decide whether to continue or end"""
    
    if state.final_answer:
        return "end"
    elif state.iteration > 2:
        return "end"
    elif len(state.tool_calls) > 0:
        return "tools"
    else:
        return "end"


workflow = StateGraph(State)

tools = [get_formatted_context]
tool_node = ToolNode(tools)

tool_descriptions = get_tool_descriptions_from_node(tool_node)

workflow.add_node("agent_node", agent_node)
workflow.add_node("tool_node", tool_node)

workflow.add_edge(START, "agent_node")

workflow.add_conditional_edges(
    "agent_node",
    tool_router,
    {
        "tools": "tool_node",
        "end": END
    }
)

workflow.add_edge("tool_node", "agent_node")


def run_agent(question: str, thread_id: str):

    initial_state = {
        "messages": [{"role": "user", "content": question}],
        "iteration": 0,
        "available_tools": tool_descriptions
    }

    config = {"configurable": {"thread_id": thread_id}}

    with PostgresSaver.from_conn_string(config.POSTGRES_CONN_STRING) as checkpointer:

        graph = workflow.compile(checkpointer=checkpointer)

        result = graph.invoke(initial_state, config=config)

    return result


def run_agent_wrapper(question: str, thread_id: str):

    qdrant_client = QdrantClient(url=config.QDRANT_URL)

    result = run_agent(question, thread_id)

    image_url_list = []
    for id in result.get("retrieved_context_ids"):
        payload = qdrant_client.retrieve(
            collection_name=config.QDRANT_COLLECTION_NAME,
            ids=[id.id]
        )[0].payload
        image_url = payload.get("first_large_image")
        price = payload.get("price")
        if image_url:
            image_url_list.append({"image_url": image_url, "price": price, "description": id.description})

    return {
        "answer": result.get("answer"),
        "retrieved_images": image_url_list
    }
