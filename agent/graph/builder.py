from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graph.state import MiaGraphState
from agent.graph.nodes.composer import response_composer_node
from agent.graph.nodes.evaluator import evaluator_node, route_after_evaluator
from agent.graph.nodes.ingress import ingress_node, route_after_ingress
from agent.graph.nodes.memory_writer import memory_writer_node
from agent.graph.nodes.specialist import make_specialist_node
from agent.graph.nodes.supervisor import route_to_specialist, supervisor_node


def build_mia_graph(service: Any, checkpointer: Any = None) -> CompiledStateGraph:
    graph = StateGraph(MiaGraphState)

    # Add nodes (bind service parameter)
    graph.add_node("ingress", partial(ingress_node, service=service))
    graph.add_node("supervisor", partial(supervisor_node, service=service))

    # Specialist nodes
    graph.add_node("specialist_github", partial(make_specialist_node("github"), service=service))
    graph.add_node("specialist_maps", partial(make_specialist_node("maps"), service=service))
    graph.add_node("specialist_smarthome", partial(make_specialist_node("smarthome"), service=service))
    graph.add_node("specialist_code", partial(make_specialist_node("code"), service=service))
    graph.add_node("specialist_calendar", partial(make_specialist_node("calendar"), service=service))
    graph.add_node("specialist_gmail", partial(make_specialist_node("gmail"), service=service))
    graph.add_node("specialist_workspace", partial(make_specialist_node("workspace"), service=service))
    graph.add_node("specialist_google_full", partial(make_specialist_node("google_full"), service=service))
    graph.add_node("specialist_media", partial(make_specialist_node("media"), service=service))
    graph.add_node("specialist_general", partial(make_specialist_node("general"), service=service))

    graph.add_node("evaluator", partial(evaluator_node, service=service))
    graph.add_node("response_composer", partial(response_composer_node, service=service))
    graph.add_node("memory_writer", partial(memory_writer_node, service=service))

    # Entry point
    graph.set_entry_point("ingress")

    # Edges
    graph.add_conditional_edges(
        "ingress",
        route_after_ingress,
        {
            "resolved": "memory_writer",
            "needs_specialist": "supervisor",
        },
    )

    graph.add_conditional_edges(
        "supervisor",
        route_to_specialist,
        {
            "github": "specialist_github",
            "maps": "specialist_maps",
            "smarthome": "specialist_smarthome",
            "code": "specialist_code",
            "calendar": "specialist_calendar",
            "gmail": "specialist_gmail",
            "workspace": "specialist_workspace",
            "google_full": "specialist_google_full",
            "media": "specialist_media",
            "general": "specialist_general",
        },
    )

    # All specialists route to the evaluator node
    specialists = [
        "specialist_github",
        "specialist_maps",
        "specialist_smarthome",
        "specialist_code",
        "specialist_calendar",
        "specialist_gmail",
        "specialist_workspace",
        "specialist_google_full",
        "specialist_media",
        "specialist_general",
    ]
    for specialist in specialists:
        graph.add_edge(specialist, "evaluator")

    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "retry": "supervisor",
            "pass": "response_composer",
            "force_pass": "response_composer",
        },
    )

    graph.add_edge("response_composer", "memory_writer")
    graph.add_edge("memory_writer", END)

    return graph.compile(checkpointer=checkpointer)
