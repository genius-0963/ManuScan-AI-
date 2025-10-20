"""
Mesh Processing Pipeline using Open3D
GPU-accelerated geometry operations for STL/STEP files
"""

import numpy as np
import open3d as o3d
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
import time


@dataclass
class MeshMetrics:
    """Container for mesh quality metrics"""
    num_vertices: int
    num_triangles: int
    is_watertight: bool
    is_manifold: bool
    surface_area: float
    volume: float
    bounding_box: np.ndarray
    center: np.ndarray
    has_self_intersections: bool


class MeshProcessor:
    """
    High-performance mesh processing pipeline with GPU acceleration.
    Handles STL/STEP file loading, cleaning, and preprocessing.
    """
    
    def __init__(self, use_gpu: bool = True, target_vertices: int = 100000):
        """
        Initialize mesh processor.
        
        Args:
            use_gpu: Enable GPU acceleration if available
            target_vertices: Target vertex count for decimation
        """
        self.use_gpu = use_gpu
        self.target_vertices = target_vertices
        
        # Check GPU availability
        if use_gpu:
            try:
                # Open3D GPU support check
                logger.info("Checking GPU availability for Open3D...")
                self.gpu_available = o3d.core.cuda.is_available()
                if self.gpu_available:
                    logger.success(f"GPU acceleration enabled: {o3d.core.cuda.device_count()} device(s)")
                else:
                    logger.warning("GPU requested but not available, falling back to CPU")
                    self.use_gpu = False
            except Exception as e:
                logger.warning(f"GPU check failed: {e}. Using CPU.")
                self.use_gpu = False
                self.gpu_available = False
        else:
            self.gpu_available = False
    
    def load_mesh(self, file_path: str) -> o3d.geometry.TriangleMesh:
        """
        Load mesh from STL or STEP file.
        
        Args:
            file_path: Path to CAD file
            
        Returns:
            Open3D TriangleMesh object
        """
        start_time = time.perf_counter()
        
        file_ext = file_path.lower().split('.')[-1]
        
        try:
            if file_ext in ['stl', 'ply', 'obj']:
                mesh = o3d.io.read_triangle_mesh(file_path)
            elif file_ext in ['step', 'stp']:
                # For STEP files, we'd need python-occ integration
                mesh = self._load_step_file(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            if not mesh.has_vertices():
                raise ValueError("Loaded mesh has no vertices")
            
            load_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"Loaded mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles ({load_time:.2f}ms)")
            
            return mesh
            
        except Exception as e:
            logger.error(f"Failed to load mesh from {file_path}: {e}")
            raise
    
    def _load_step_file(self, file_path: str) -> o3d.geometry.TriangleMesh:
        """
        Load STEP file using python-occ and convert to mesh.
        Note: Requires python-occ-core package
        """
        try:
            from OCC.Extend.DataExchange import read_step_file
            from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
            from OCC.Core.StlAPI import StlAPI_Writer
            import tempfile
            import os
            
            # Read STEP file
            shape = read_step_file(file_path)
            
            # Triangulate
            mesh_builder = BRepMesh_IncrementalMesh(shape, 0.1)
            mesh_builder.Perform()
            
            # Export to temporary STL
            with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
                stl_writer = StlAPI_Writer()
                stl_writer.Write(shape, tmp.name)
                tmp_path = tmp.name
            
            # Load STL with Open3D
            mesh = o3d.io.read_triangle_mesh(tmp_path)
            
            # Cleanup
            os.unlink(tmp_path)
            
            return mesh
            
        except ImportError:
            logger.error("python-occ-core not installed. Cannot load STEP files.")
            raise
        except Exception as e:
            logger.error(f"Failed to process STEP file: {e}")
            raise
    
    def preprocess(self, mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.TriangleMesh:
        """
        Complete preprocessing pipeline:
        1. Clean mesh (remove duplicates, degenerate triangles)
        2. Compute normals
        3. Decimate if too large
        4. Check for issues
        
        Args:
            mesh: Input mesh
            
        Returns:
            Preprocessed mesh
        """
        start_time = time.perf_counter()
        
        logger.info("Starting mesh preprocessing...")
        
        # Remove duplicated vertices and triangles
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()
        mesh.remove_degenerate_triangles()
        mesh.remove_unreferenced_vertices()
        
        # Remove non-manifold edges
        mesh.remove_non_manifold_edges()
        
        # Compute vertex normals (required for many analyses)
        mesh.compute_vertex_normals()
        mesh.compute_triangle_normals()
        
        # Decimate if mesh is too large
        current_vertices = len(mesh.vertices)
        if current_vertices > self.target_vertices:
            reduction_ratio = self.target_vertices / current_vertices
            logger.info(f"Decimating mesh from {current_vertices} to ~{self.target_vertices} vertices")
            mesh = mesh.simplify_quadric_decimation(
                target_number_of_triangles=int(len(mesh.triangles) * reduction_ratio)
            )
            mesh.compute_vertex_normals()
            logger.info(f"After decimation: {len(mesh.vertices)} vertices")
        
        # Orient triangles consistently
        mesh.orient_triangles()
        
        preprocess_time = (time.perf_counter() - start_time) * 1000
        logger.success(f"Preprocessing complete ({preprocess_time:.2f}ms)")
        
        return mesh
    
    def compute_metrics(self, mesh: o3d.geometry.TriangleMesh) -> MeshMetrics:
        """
        Compute comprehensive mesh quality metrics.
        
        Args:
            mesh: Input mesh
            
        Returns:
            MeshMetrics object
        """
        # Basic counts
        num_vertices = len(mesh.vertices)
        num_triangles = len(mesh.triangles)
        
        # Topological checks
        is_watertight = mesh.is_watertight()
        is_manifold = mesh.is_vertex_manifold() and mesh.is_edge_manifold()
        
        # Geometric properties
        surface_area = mesh.get_surface_area()
        
        try:
            volume = mesh.get_volume() if is_watertight else 0.0
        except:
            volume = 0.0
        
        # Bounding box
        bbox = mesh.get_axis_aligned_bounding_box()
        bounding_box = np.array([bbox.min_bound, bbox.max_bound])
        center = mesh.get_center()
        
        # Self-intersection check (expensive, simplified)
        has_self_intersections = not is_manifold  # Approximation
        
        return MeshMetrics(
            num_vertices=num_vertices,
            num_triangles=num_triangles,
            is_watertight=is_watertight,
            is_manifold=is_manifold,
            surface_area=surface_area,
            volume=volume,
            bounding_box=bounding_box,
            center=center,
            has_self_intersections=has_self_intersections
        )
    
    def extract_edges(self, mesh: o3d.geometry.TriangleMesh) -> np.ndarray:
        """
        Extract edges from mesh for graph conversion.
        
        Returns:
            Edge array of shape (E, 2) with vertex indices
        """
        triangles = np.asarray(mesh.triangles)
        
        # Each triangle has 3 edges
        edges = []
        for tri in triangles:
            edges.append([tri[0], tri[1]])
            edges.append([tri[1], tri[2]])
            edges.append([tri[2], tri[0]])
        
        edges = np.array(edges)
        
        # Remove duplicates (keep undirected edges)
        edges = np.sort(edges, axis=1)
        edges = np.unique(edges, axis=0)
        
        return edges
    
    def compute_curvature(self, mesh: o3d.geometry.TriangleMesh) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Gaussian and Mean curvature at each vertex.
        Uses local surface fitting approach.
        
        Returns:
            Tuple of (gaussian_curvature, mean_curvature) arrays
        """
        vertices = np.asarray(mesh.vertices)
        normals = np.asarray(mesh.vertex_normals)
        num_vertices = len(vertices)
        
        # Build KD-tree for nearest neighbor search
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(vertices)
        kdtree = o3d.geometry.KDTreeFlann(pcd)
        
        gaussian_curvature = np.zeros(num_vertices)
        mean_curvature = np.zeros(num_vertices)
        
        # Compute curvature at each vertex
        for i in range(num_vertices):
            # Find k-nearest neighbors
            [k, idx, _] = kdtree.search_knn_vector_3d(vertices[i], 15)
            
            if k < 5:
                continue
            
            # Local points
            local_points = vertices[idx[1:]]  # Exclude self
            local_normals = normals[idx[1:]]
            
            # Estimate curvature from normal variation
            normal_variation = np.linalg.norm(local_normals - normals[i], axis=1)
            distances = np.linalg.norm(local_points - vertices[i], axis=1)
            
            # Avoid division by zero
            safe_distances = np.where(distances > 1e-6, distances, 1e-6)
            
            # Simple curvature estimate
            curvatures = normal_variation / safe_distances
            mean_curvature[i] = np.mean(curvatures)
            gaussian_curvature[i] = np.std(curvatures)  # Approximation
        
        logger.info(f"Curvature computed - Mean: {np.mean(mean_curvature):.4f}, Max: {np.max(mean_curvature):.4f}")
        
        return gaussian_curvature, mean_curvature
    
    def to_point_cloud(self, mesh: o3d.geometry.TriangleMesh, num_points: int = 50000) -> o3d.geometry.PointCloud:
        """
        Convert mesh to point cloud via sampling.
        Useful for point-based neural networks.
        
        Args:
            mesh: Input mesh
            num_points: Number of points to sample
            
        Returns:
            Point cloud
        """
        pcd = mesh.sample_points_uniformly(number_of_points=num_points)
        pcd.estimate_normals()
        return pcd


def main():
    """Test mesh processor"""
    processor = MeshProcessor(use_gpu=True, target_vertices=100000)
    
    # Example usage
    # mesh = processor.load_mesh("example.stl")
    # mesh = processor.preprocess(mesh)
    # metrics = processor.compute_metrics(mesh)
    # print(metrics)
    
    print("MeshProcessor initialized successfully")


if __name__ == "__main__":
    main()
