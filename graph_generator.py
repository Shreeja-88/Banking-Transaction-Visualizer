import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def build_precedence_graph(conflicts):
    """
    conflicts: list of (tid1, tid2, account, reason)
    Returns a directed graph (DiGraph).
    """
    G = nx.DiGraph()
    for tid1, tid2, account, reason in conflicts:
        G.add_edge(tid1, tid2, label=account)
    return G


def draw_graph(G, is_safe, ax=None, title="Precedence Graph"):
    """
    Draw the precedence graph on the given axes.
    Colors nodes red if a cycle exists (unsafe), green if safe.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))

    ax.clear()

    if len(G.nodes) == 0:
        ax.text(0.5, 0.5, "No conflicts detected\nAll transactions are safe",
                ha='center', va='center', fontsize=12,
                color='green', transform=ax.transAxes)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.axis('off')
        return

    node_color = "#e74c3c" if not is_safe else "#2ecc71"
    edge_color = "#c0392b" if not is_safe else "#27ae60"

    try:
        pos = nx.spring_layout(G, seed=42)
    except Exception:
        pos = nx.circular_layout(G)

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_color,
                           node_size=1800, alpha=0.9)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=12,
                            font_color='white', font_weight='bold')
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_color,
                           arrows=True, arrowsize=25,
                           connectionstyle='arc3,rad=0.1',
                           width=2)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 ax=ax, font_size=9, font_color='#2c3e50')

    status = "⚠ UNSAFE — Cycle Detected!" if not is_safe else "✓ SAFE — No Cycle"
    color = "#e74c3c" if not is_safe else "#27ae60"
    ax.set_title(f"{title}\n{status}", fontsize=12, fontweight='bold', color=color)
    ax.axis('off')
