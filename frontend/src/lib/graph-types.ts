export interface GraphNode {
  node_id: string;
  repo_id?: string;
  name?: string;
  label?: string;
  file_path?: string;
  path?: string;
  start_line?: number;
  end_line?: number;
  extends?: string;
  is_async?: boolean;
  is_exported?: boolean;
  method?: string;
}

export interface GraphRelationship {
  type: string;
  from_id: string;
  from_name: string;
  to_id: string;
  to_name: string;
}

export interface GraphSummary {
  repo_id: string;
  owner: string;
  name: string;
  nodes: Record<string, number>;
  relationships: Record<string, number>;
}

export interface GraphNodeDetail {
  node: GraphNode;
  outgoing: {
    rel_type: string;
    target_id: string;
    target_name: string;
    target_label: string;
  }[];
  incoming: {
    rel_type: string;
    source_id: string;
    source_name: string;
    source_label: string;
  }[];
}
