#define main gap_original_main
#include "bfs.cc"
#undef main

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <queue>
#include <stdexcept>

std::vector<int> QueueDistances(const Graph &graph, NodeID source) {
  std::vector<int> distances(graph.num_nodes(), -1);
  std::queue<NodeID> frontier;
  distances[source] = 0;
  frontier.push(source);
  while (!frontier.empty()) {
    const auto u = frontier.front();
    frontier.pop();
    for (auto v : graph.out_neigh(u)) {
      if (distances[v] >= 0) continue;
      distances[v] = distances[u] + 1;
      frontier.push(v);
    }
  }
  return distances;
}

void CheckParents(const Graph &graph, NodeID source,
                  const pvector<NodeID> &parent,
                  const std::vector<int> &distance) {
  if (parent[source] != source) throw std::runtime_error("Invalid root");
  for (NodeID vertex : graph.vertices()) {
    if (vertex == source) continue;
    const auto predecessor = parent[vertex];
    if (distance[vertex] == -1) {
      if (predecessor != -1) throw std::runtime_error("Reached disconnected vertex");
      continue;
    }
    if (predecessor < 0 || predecessor >= graph.num_nodes() ||
        distance[predecessor] != distance[vertex] - 1) {
      throw std::runtime_error("Invalid predecessor distance");
    }
    auto neighbors = graph.in_neigh(vertex);
    if (std::find(neighbors.begin(), neighbors.end(), predecessor) == neighbors.end())
      throw std::runtime_error("Missing parent edge");
  }
}

pvector<NodeID> TopDown(const Graph &graph, NodeID source) {
  auto parent = InitParent(graph);
  SlidingQueue<NodeID> frontier(graph.num_nodes());
  parent[source] = source;
  frontier.push_back(source);
  frontier.slide_window();
  while (!frontier.empty()) {
    TDStep(graph, parent, frontier);
    frontier.slide_window();
  }
  for (auto &value : parent) if (value < -1) value = -1;
  return parent;
}

int main(int argc, char **argv) {
  CLApp cli(argc, argv, "verified BFS audit");
  if (!cli.ParseArgs() || !cli.symmetrize()) return 2;
  Timer timer;
  timer.Start();
  Builder builder(cli);
  Graph graph = builder.MakeGraph();
  timer.Stop();
  cout << "audit graph " << graph.num_nodes() << ' ' << graph.num_edges()
       << ' ' << timer.Seconds() << '\n';
  NodeID isolated = 0;
  vector<NodeID> sources;
  for (NodeID vertex : graph.vertices()) {
    if (graph.out_degree(vertex) == 0) ++isolated;
    else if (sources.size() < 3) sources.push_back(vertex);
  }
  if (sources.size() != 3) throw std::runtime_error("Expected three nonisolated sources");
  cout << "audit isolated " << isolated << '\n';
  ofstream graph_file("graph-edges.txt");
  graph_file << graph.num_nodes() << ' ' << graph.num_edges() << '\n';
  for (NodeID u : graph.vertices())
    for (auto v : graph.out_neigh(u)) if (u < v) graph_file << u << ' ' << v << '\n';

  for (auto source : sources) {
    const auto distances = QueueDistances(graph, source);
    timer.Start();
    auto direction_optimizing = DOBFS(graph, source, false);
    timer.Stop();
    const auto direction_time = timer.Seconds();
    timer.Start();
    auto top_down = TopDown(graph, source);
    timer.Stop();
    const auto top_down_time = timer.Seconds();
    for (auto result : {&direction_optimizing, &top_down}) {
      CheckParents(graph, source, *result, distances);
      if (!BFSVerifier(graph, source, *result))
        throw std::runtime_error("GAP verifier failed");
    }
    cout << "audit source " << source << ' ' << direction_time << ' ' << top_down_time << '\n';
    auto traced = DOBFS(graph, source, true);
    CheckParents(graph, source, traced, distances);
    ofstream certificate("distances-" + to_string(source) + ".txt");
    for (auto depth : distances) certificate << depth << '\n';
  }
}
