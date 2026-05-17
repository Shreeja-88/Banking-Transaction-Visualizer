def _dfs(node, visited, rec_stack, graph):
    """
    Recursive DFS helper.
    Returns True if a cycle is found from `node`.
    """
    visited.add(node)
    rec_stack.add(node)

    for neighbor in graph.get(node, []):
        if neighbor not in visited:
            if _dfs(neighbor, visited, rec_stack, graph):
                return True
        elif neighbor in rec_stack:
            return True

    rec_stack.remove(node)
    return False


def has_cycle(G):
    """
    G: networkx DiGraph
    Returns True if cycle exists (schedule is UNSAFE).
    """
    # Convert to adjacency dict
    graph = {node: list(G.successors(node)) for node in G.nodes}

    visited = set()
    rec_stack = set()

    for node in graph:
        if node not in visited:
            if _dfs(node, visited, rec_stack, graph):
                return True
    return False


def find_cycle_path(G):
    """
    Returns the cycle path as a list of nodes, or [] if no cycle.
    Uses networkx built-in for convenience.
    """
    import networkx as nx
    try:
        cycle = nx.find_cycle(G, orientation='original')
        return [e[0] for e in cycle] + [cycle[-1][1]]
    except nx.NetworkXNoCycle:
        return []
