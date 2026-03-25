import json
import logging
from typing import Dict, Any, List

import networkx as nx

from . import neo4j_store
from ..utils.llm_client import LLMClient

logger = logging.getLogger("neofish.community_summarizer")

class CommunitySummarizer:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()

    def build_and_summarize_communities(self, graph_id: str):
        logger.info(f"Building communities for graph {graph_id}...")
        nodes = neo4j_store.fetch_nodes(graph_id)
        edges = neo4j_store.fetch_edges(graph_id)

        if not nodes:
            logger.warning(f"No nodes found for graph {graph_id}, skipping community detection.")
            return

        G = nx.Graph()
        
        # Add nodes
        node_lookup = {}
        for node in nodes:
            uuid = node["uuid"]
            name = node.get("name", "Unknown")
            G.add_node(uuid, name=name, summary=node.get("summary", ""))
            node_lookup[uuid] = node

        # Add edges
        for edge in edges:
            source = edge.get("source_node_uuid")
            target = edge.get("target_node_uuid")
            if source and target and G.has_node(source) and G.has_node(target):
                G.add_edge(source, target, type=edge.get("name", ""), fact=edge.get("fact", ""))

        # Use Louvain algorithm for community detection
        try:
            from networkx.algorithms import community
            communities = community.louvain_communities(G)
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return

        logger.info(f"Detected {len(communities)} communities for graph {graph_id}.")

        summaries = []
        for i, comm in enumerate(communities):
            comm_nodes = [node_lookup[u] for u in comm]
            if len(comm_nodes) < 3:
                continue # Skip very small communities

            # Gather facts from intra-community edges
            comm_subgraph = G.subgraph(comm)
            comm_edges = list(comm_subgraph.edges(data=True))

            summary = self._summarize_community(i, comm_nodes, comm_edges)
            if summary:
                summaries.append({
                    "community_id": f"{graph_id}-comm-{i}",
                    "summary": summary,
                    "node_uuids": list(comm)
                })

        if summaries:
            logger.info(f"Storing {len(summaries)} community summaries...")
            neo4j_store.store_community_summaries(graph_id, summaries)
            logger.info("Community summarization complete.")

    def _summarize_community(self, comm_index: int, nodes: List[Dict], edges: List) -> str:
        entities_text = ", ".join([n.get("name", "Unknown") for n in nodes[:50]]) # Limit to avoid huge prompts
        facts_text = "\n".join([f"- {u} to {v}: {d.get('fact', d.get('type'))}" for u, v, d in edges[:50]])

        system_prompt = "You are an expert data analyst. Summarize the overall theme and key interactions within this network community."
        user_prompt = f"""
Community Entities: {entities_text}

Key Interactions:
{facts_text}

Provide a concise, comprehensive paragraph summarizing the overarching theme, purpose, and key activities within this community. Do not list entities, instead describe what they collectively represent.
"""
        try:
            summary = self.llm.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to summarize community {comm_index}: {e}")
            return ""
