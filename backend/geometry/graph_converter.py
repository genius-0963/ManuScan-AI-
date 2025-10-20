"""
Convert 3D meshes to graph representations for GNN processing
"""

import numpy as np
import open3d as o3d
import torch
from torch_geometric.data import Data
from typing import Tuple, Optional, Dict
from loguru import logger


class MeshToGraphConverter:
    """
    Converts triangle meshes to graph representations suitable for GNN processing.
    Vertices become nodes, edges are derived from mesh connectivity.
    """
    
    def __init__(self, k_neighbors: int = 8, use_edge_features: bool = True):
        """
        Args:
            k_neighbors: Number of nearest neighbors for edge creation
            use_edge_features: Include edge attributes (distance, angle)
        """
        self.k_neighbors = k_neighbors
        self.use_edge_features = use_edge_features
    
    def convert(
        self,
        mesh: o3d.geometry.TriangleMesh,
        thickness_map: Optional[np.ndarray] = None,
        undercut_labels: Optional[np.ndarray] = None
    ) -> Data:
        """
        Convert mesh to PyTorch Geometric Data object.
        
        Args:
            mesh: Input mesh
            thickness_map: Per-vertex thickness values (optional labels)
            undercut_labels: Per-vertex undercut labels (optional)
            
        Returns:
            PyTorch Geometric Data object
        """
        # Extract node features
        node_features = self.extract_node_features(mesh)
        
        # Extract edges from mesh topology
        edge_index, edge_attr = self.extract_edges(mesh)
        
        # Create Data object
        data = Data(
            x=torch.from_numpy(node_features).float(),
            edge_index=torch.from_numpy(edge_index).long(),
        )
        
        if self.use_edge_features and edge_attr is not None:
            data.edge_attr = torch.from_numpy(edge_attr).float()
        
        # Add labels if provided
        if thickness_map is not None:
            data.y_thickness = torch.from_numpy(thickness_map).float().unsqueeze(-1)
        
        if undercut_labels is not None:
            data.y_undercut = torch.from_numpy(undercut_labels).float().unsqueeze(-1)
        
        # Add mesh statistics
        data.num_nodes = len(node_features)
        
        logger.info(f"Graph created: {data.num_nodes} nodes, {data.edge_index.shape[1]} edges")
        
        return data
    
    def extract_node_features(self, mesh: o3d.geometry.TriangleMesh) -> np.ndarray:
        """
        Extract per-vertex features.
        
        Features include:
        - Position (x, y, z)
        - Normal (nx, ny, nz)
        - Curvature (optional)
        - Local density
        
        Returns:
            Node feature matrix [num_vertices, feature_dim]
        """
        vertices = np.asarray(mesh.vertices)
        
        # Ensure normals exist
        if not mesh.has_vertex_normals():
            mesh.compute_vertex_normals()
        normals = np.asarray(mesh.vertex_normals)
        
        # Basic features: position + normal
        features = np.concatenate([vertices, normals], axis=1)  # [N, 6]
        
        # Add curvature estimates (optional)
        if mesh.has_triangle_normals():
            curvature = self.estimate_curvature(mesh)
            features = np.concatenate([features, curvature.reshape(-1, 1)], axis=1)  # [N, 7]
        
        # Normalize positions to unit sphere
        center = np.mean(vertices, axis=0)
        vertices_centered = vertices - center
        scale = np.max(np.linalg.norm(vertices_centered, axis=1))
        features[:, :3] = vertices_centered / (scale + 1e-8)
        
        return features.astype(np.float32)
    
    def extract_edges(self, mesh: o3d.geometry.TriangleMesh) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Extract edge connectivity from mesh.
        
        Returns:
            edge_index: [2, num_edges] array
            edge_attr: [num_edges, edge_feature_dim] array (optional)
        """
        triangles = np.asarray(mesh.triangles)
        vertices = np.asarray(mesh.vertices)
        
        # Extract edges from triangles
        edges_list = []
        for tri in triangles:
            edges_list.append([tri[0], tri[1]])
            edges_list.append([tri[1], tri[2]])
            edges_list.append([tri[2], tri[0]])
            # Add reverse edges for undirected graph
            edges_list.append([tri[1], tri[0]])
            edges_list.append([tri[2], tri[1]])
            edges_list.append([tri[0], tri[2]])
        
        edges = np.array(edges_list, dtype=np.int64).T  # [2, num_edges]
        
        # Remove duplicate edges
        edges_unique = np.unique(edges, axis=1)
        
        # Compute edge features
        edge_attr = None
        if self.use_edge_features:
            edge_vectors = vertices[edges_unique[1]] - vertices[edges_unique[0]]
            edge_lengths = np.linalg.norm(edge_vectors, axis=1, keepdims=True)
            edge_attr = edge_lengths.astype(np.float32)
        
        return edges_unique, edge_attr
    
    def estimate_curvature(self, mesh: o3d.geometry.TriangleMesh) -> np.ndarray:
        """
        Estimate mean curvature at each vertex.
        Simple approximation based on normal variation.
        """
        vertices = np.asarray(mesh.vertices)
        normals = np.asarray(mesh.vertex_normals)
        triangles = np.asarray(mesh.triangles)
        
        num_vertices = len(vertices)
        curvature = np.zeros(num_vertices)
        
        # Build vertex-to-triangles adjacency
        vertex_triangles = [[] for _ in range(num_vertices)]
        for tri_idx, tri in enumerate(triangles):
            for v in tri:
                vertex_triangles[v].append(tri_idx)
        
        # Estimate curvature from neighboring normals
        for v_idx in range(num_vertices):
            if len(vertex_triangles[v_idx]) == 0:
                continue
            
            # Get neighbor vertices
            neighbors = set()
            for tri_idx in vertex_triangles[v_idx]:
                neighbors.update(triangles[tri_idx])
            neighbors.discard(v_idx)
            
            if len(neighbors) == 0:
                continue
            
            # Compute normal variation
            neighbor_normals = normals[list(neighbors)]
            normal_diff = np.linalg.norm(neighbor_normals - normals[v_idx], axis=1)
            curvature[v_idx] = np.mean(normal_diff)
        
        # Normalize
        curvature = (curvature - np.mean(curvature)) / (np.std(curvature) + 1e-8)
        
        return curvature
    
    def batch_convert(self, meshes: list, labels: Optional[list] = None) -> list:
        """
        Convert multiple meshes to graphs.
        
        Args:
            meshes: List of Open3D meshes
            labels: Optional list of label dictionaries
            
        Returns:
            List of Data objects
        """
        graphs = []
        
        for i, mesh in enumerate(meshes):
            thickness = labels[i].get('thickness') if labels and i < len(labels) else None
            undercuts = labels[i].get('undercuts') if labels and i < len(labels) else None
            
            graph = self.convert(mesh, thickness, undercuts)
            graphs.append(graph)
        
        return graphs


def create_synthetic_labels(mesh: o3d.geometry.TriangleMesh) -> Dict[str, np.ndarray]:
    """
    Create synthetic labels for testing (random values).
    In production, these would come from actual analysis or manual annotation.
    """
    num_vertices = len(mesh.vertices)
    
    return {
        'thickness': np.random.uniform(1.0, 10.0, num_vertices),
        'undercuts': np.random.randint(0, 2, num_vertices).astype(np.float32),
        'sharp_edges': np.random.randint(0, 2, num_vertices).astype(np.float32)
    }


def main():
    """Test graph converter"""
    converter = MeshToGraphConverter(k_neighbors=8, use_edge_features=True)
    
    # Create a simple test mesh
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=20)
    mesh.compute_vertex_normals()
    
    # Convert to graph
    graph = converter.convert(mesh)
    
    print(f"Graph statistics:")
    print(f"  Nodes: {graph.num_nodes}")
    print(f"  Edges: {graph.edge_index.shape[1]}")
    print(f"  Node features: {graph.x.shape}")
    if hasattr(graph, 'edge_attr'):
        print(f"  Edge features: {graph.edge_attr.shape}")
    
    print("\n✓ Graph converter working correctly")


if __name__ == "__main__":
    main()
