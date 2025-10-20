#!/usr/bin/env python3
"""
ManuScan AI - Example Usage
Demonstrates how to use the Python API for geometry analysis
"""

import open3d as o3d
from backend.geometry.mesh_processor import MeshProcessor
from backend.geometry.feature_detection import FeatureDetector
from backend.geometry.graph_converter import MeshToGraphConverter
from backend.models.gnn_architecture import create_model
import torch


def example_basic_analysis():
    """Example: Basic manufacturability analysis"""
    print("=" * 60)
    print("Example 1: Basic Manufacturability Analysis")
    print("=" * 60)
    
    # Create a test mesh (sphere)
    print("\n1. Creating test mesh...")
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=10.0, resolution=30)
    mesh.compute_vertex_normals()
    print(f"   ✓ Created sphere with {len(mesh.vertices)} vertices")
    
    # Initialize processor
    print("\n2. Initializing mesh processor...")
    processor = MeshProcessor(use_gpu=True, target_vertices=10000)
    
    # Preprocess
    print("\n3. Preprocessing mesh...")
    mesh = processor.preprocess(mesh)
    metrics = processor.compute_metrics(mesh)
    print(f"   ✓ Vertices: {metrics.num_vertices}")
    print(f"   ✓ Triangles: {metrics.num_triangles}")
    print(f"   ✓ Is watertight: {metrics.is_watertight}")
    print(f"   ✓ Surface area: {metrics.surface_area:.2f}")
    
    # Analyze features
    print("\n4. Analyzing manufacturability...")
    detector = FeatureDetector(
        min_wall_thickness=2.0,
        min_draft_angle=3.0,
        sharp_edge_threshold=30.0
    )
    
    report = detector.generate_report(mesh)
    
    print(f"\n   📊 RESULTS:")
    print(f"   ├─ Overall Score: {report.overall_score:.1f}/100")
    print(f"   ├─ Min Thickness: {report.thickness.min_thickness:.2f}mm")
    print(f"   ├─ Thin Walls: {len(report.thickness.thin_regions)}")
    print(f"   ├─ Undercuts: {len(report.undercuts)}")
    print(f"   └─ Sharp Edges: {len(report.sharp_edges)}")
    
    return report


def example_graph_conversion():
    """Example: Convert mesh to graph for GNN"""
    print("\n" + "=" * 60)
    print("Example 2: Graph Conversion for GNN")
    print("=" * 60)
    
    # Create mesh
    print("\n1. Creating test mesh...")
    mesh = o3d.geometry.TriangleMesh.create_box(width=10, height=10, depth=10)
    mesh.compute_vertex_normals()
    
    # Convert to graph
    print("\n2. Converting mesh to graph...")
    converter = MeshToGraphConverter(k_neighbors=8, use_edge_features=True)
    graph = converter.convert(mesh)
    
    print(f"\n   📊 GRAPH STATISTICS:")
    print(f"   ├─ Nodes: {graph.num_nodes}")
    print(f"   ├─ Edges: {graph.edge_index.shape[1]}")
    print(f"   ├─ Node features: {graph.x.shape}")
    print(f"   └─ Edge features: {graph.edge_attr.shape if hasattr(graph, 'edge_attr') else 'None'}")
    
    return graph


def example_model_inference():
    """Example: Run GNN model inference"""
    print("\n" + "=" * 60)
    print("Example 3: GNN Model Inference")
    print("=" * 60)
    
    # Create mesh and convert to graph
    print("\n1. Preparing data...")
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=5.0, resolution=20)
    mesh.compute_vertex_normals()
    
    converter = MeshToGraphConverter()
    graph = converter.convert(mesh)
    
    # Create model
    print("\n2. Creating GNN model...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = create_model(
        model_type='gcn',
        in_channels=6,
        hidden_channels=128,
        num_layers=4
    ).to(device)
    
    print(f"   ✓ Model created on {device}")
    print(f"   ✓ Parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Run inference
    print("\n3. Running inference...")
    model.eval()
    
    with torch.no_grad():
        x = graph.x.to(device)
        edge_index = graph.edge_index.to(device)
        
        output = model(x, edge_index)
    
    print(f"\n   📊 MODEL OUTPUT:")
    print(f"   ├─ Thickness predictions: {output['thickness'].shape}")
    print(f"   ├─ Undercut predictions: {output['undercut'].shape}")
    print(f"   ├─ Sharp edge predictions: {output['sharp_edge'].shape}")
    print(f"   └─ Overall score: {output['overall_score'].item():.3f}")
    
    return output


def example_save_visualization():
    """Example: Save analysis visualization"""
    print("\n" + "=" * 60)
    print("Example 4: Save Visualization")
    print("=" * 60)
    
    # Create and analyze mesh
    print("\n1. Analyzing mesh...")
    mesh = o3d.geometry.TriangleMesh.create_torus(
        torus_radius=10.0,
        tube_radius=2.0,
        radial_resolution=30,
        tubular_resolution=20
    )
    mesh.compute_vertex_normals()
    
    processor = MeshProcessor()
    mesh = processor.preprocess(mesh)
    
    detector = FeatureDetector()
    thickness_result = detector.analyze_wall_thickness(mesh)
    
    # Color mesh by thickness
    print("\n2. Creating visualization...")
    import numpy as np
    
    thickness = thickness_result.thickness_map
    colors = np.zeros((len(mesh.vertices), 3))
    
    # Normalize thickness to [0, 1]
    valid_thickness = thickness[thickness < np.inf]
    if len(valid_thickness) > 0:
        t_min, t_max = np.min(valid_thickness), np.max(valid_thickness)
        normalized = np.clip((thickness - t_min) / (t_max - t_min + 1e-8), 0, 1)
        
        # Red-yellow-green colormap
        for i in range(len(mesh.vertices)):
            val = normalized[i]
            if val < 0.5:
                colors[i] = [1, val * 2, 0]  # Red to yellow
            else:
                colors[i] = [1 - (val - 0.5) * 2, 1, 0]  # Yellow to green
    
    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    
    # Save
    output_file = "thickness_visualization.ply"
    o3d.io.write_triangle_mesh(output_file, mesh)
    print(f"\n   ✓ Visualization saved to: {output_file}")
    print(f"   ✓ Open with: o3d.visualization.draw_geometries([mesh])")


def main():
    """Run all examples"""
    print("\n" + "🔍" * 30)
    print("ManuScan AI - Example Usage")
    print("🔍" * 30 + "\n")
    
    try:
        # Example 1: Basic analysis
        report = example_basic_analysis()
        
        # Example 2: Graph conversion
        graph = example_graph_conversion()
        
        # Example 3: Model inference
        output = example_model_inference()
        
        # Example 4: Visualization
        example_save_visualization()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
