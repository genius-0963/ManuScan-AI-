"""
Advanced Geometric Feature Detection
Detects manufacturability issues: wall thickness, undercuts, sharp edges, draft angles
"""

import numpy as np
import open3d as o3d
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from loguru import logger
import time
from enum import Enum


class IssueLevel(Enum):
    """Severity levels for manufacturability issues"""
    CRITICAL = "critical"  # Will fail manufacturing
    WARNING = "warning"    # May cause issues
    ACCEPTABLE = "acceptable"  # Within tolerances


@dataclass
class ThicknessResult:
    """Wall thickness analysis result"""
    min_thickness: float
    max_thickness: float
    mean_thickness: float
    thin_regions: List[int]  # Vertex indices
    thickness_map: np.ndarray  # Per-vertex thickness


@dataclass
class UndercutRegion:
    """Detected undercut region"""
    vertex_indices: List[int]
    severity: float  # 0-1 scale
    draft_direction: np.ndarray
    issue_level: IssueLevel


@dataclass
class SharpEdge:
    """Sharp edge detection result"""
    vertex_pairs: List[Tuple[int, int]]
    angle: float  # In degrees
    location: np.ndarray


@dataclass
class ManufacturabilityReport:
    """Complete manufacturability analysis"""
    thickness: ThicknessResult
    undercuts: List[UndercutRegion]
    sharp_edges: List[SharpEdge]
    draft_angles: np.ndarray  # Per-face draft angles
    overall_score: float  # 0-100 manufacturability score
    issues_summary: Dict[str, int]


class FeatureDetector:
    """
    Detects geometric features critical for manufacturability.
    Implements advanced algorithms for thickness, undercut, and curvature analysis.
    """
    
    def __init__(
        self,
        min_wall_thickness: float = 2.0,  # mm
        min_draft_angle: float = 3.0,  # degrees
        sharp_edge_threshold: float = 30.0,  # degrees
        undercut_ray_samples: int = 100
    ):
        """
        Initialize feature detector with manufacturing constraints.
        
        Args:
            min_wall_thickness: Minimum acceptable wall thickness (mm)
            min_draft_angle: Minimum draft angle for molding (degrees)
            sharp_edge_threshold: Maximum angle for sharp edge detection
            undercut_ray_samples: Number of rays for undercut detection
        """
        self.min_wall_thickness = min_wall_thickness
        self.min_draft_angle = min_draft_angle
        self.sharp_edge_threshold = sharp_edge_threshold
        self.undercut_ray_samples = undercut_ray_samples
    
    def analyze_wall_thickness(
        self,
        mesh: o3d.geometry.TriangleMesh,
        num_rays: int = 32
    ) -> ThicknessResult:
        """
        Analyze wall thickness using ray casting.
        Casts rays from each vertex in normal direction to find opposing surface.
        
        Args:
            mesh: Input mesh
            num_rays: Number of rays per vertex (directional sampling)
            
        Returns:
            ThicknessResult with thickness map
        """
        start_time = time.perf_counter()
        logger.info("Analyzing wall thickness...")
        
        vertices = np.asarray(mesh.vertices)
        normals = np.asarray(mesh.vertex_normals)
        num_vertices = len(vertices)
        
        # Create raycasting scene
        mesh_legacy = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
        scene = o3d.t.geometry.RaycastingScene()
        scene.add_triangles(mesh_legacy)
        
        thickness_map = np.full(num_vertices, np.inf)
        
        # Cast rays from each vertex
        for i in range(num_vertices):
            origin = vertices[i]
            normal = normals[i]
            
            # Cast rays in multiple directions around normal
            min_dist = np.inf
            
            # Primary ray (along negative normal)
            rays = o3d.core.Tensor([[*origin, *(-normal)]], dtype=o3d.core.Dtype.Float32)
            result = scene.cast_rays(rays)
            
            t_hit = result['t_hit'].numpy()[0]
            if np.isfinite(t_hit) and t_hit > 0.01:  # Avoid self-intersection
                min_dist = min(min_dist, t_hit)
            
            # Additional rays with slight angular variation
            for angle_offset in np.linspace(-0.3, 0.3, 5):  # ±17 degrees
                # Perturb normal direction
                perturbed_normal = self._rotate_vector(normal, angle_offset)
                rays = o3d.core.Tensor([[*origin, *(-perturbed_normal)]], dtype=o3d.core.Dtype.Float32)
                result = scene.cast_rays(rays)
                
                t_hit = result['t_hit'].numpy()[0]
                if np.isfinite(t_hit) and t_hit > 0.01:
                    min_dist = min(min_dist, t_hit)
            
            thickness_map[i] = min_dist if np.isfinite(min_dist) else 0.0
        
        # Identify thin regions
        thin_regions = np.where(
            (thickness_map > 0) & (thickness_map < self.min_wall_thickness)
        )[0].tolist()
        
        # Statistics
        valid_thickness = thickness_map[thickness_map < np.inf]
        if len(valid_thickness) > 0:
            min_thickness = np.min(valid_thickness)
            max_thickness = np.max(valid_thickness)
            mean_thickness = np.mean(valid_thickness)
        else:
            min_thickness = max_thickness = mean_thickness = 0.0
        
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.success(
            f"Thickness analysis complete ({elapsed:.2f}ms): "
            f"Min={min_thickness:.2f}mm, Mean={mean_thickness:.2f}mm, "
            f"Thin regions: {len(thin_regions)}"
        )
        
        return ThicknessResult(
            min_thickness=min_thickness,
            max_thickness=max_thickness,
            mean_thickness=mean_thickness,
            thin_regions=thin_regions,
            thickness_map=thickness_map
        )
    
    def detect_undercuts(
        self,
        mesh: o3d.geometry.TriangleMesh,
        draft_direction: np.ndarray = np.array([0, 0, 1])
    ) -> List[UndercutRegion]:
        """
        Detect undercut regions preventing mold release.
        Uses normal vector analysis against draft direction.
        
        Args:
            mesh: Input mesh
            draft_direction: Mold separation direction (default: +Z)
            
        Returns:
            List of detected undercut regions
        """
        start_time = time.perf_counter()
        logger.info("Detecting undercuts...")
        
        vertices = np.asarray(mesh.vertices)
        normals = np.asarray(mesh.vertex_normals)
        
        # Normalize draft direction
        draft_direction = draft_direction / np.linalg.norm(draft_direction)
        
        # Compute angle between normal and draft direction
        dot_products = np.dot(normals, draft_direction)
        angles = np.arccos(np.clip(dot_products, -1.0, 1.0))
        angles_deg = np.degrees(angles)
        
        # Undercuts: normals pointing against draft direction (angle > 90°)
        undercut_mask = angles_deg > 90.0
        undercut_indices = np.where(undercut_mask)[0]
        
        # Cluster undercut regions
        undercut_regions = self._cluster_vertices(vertices, undercut_indices, threshold=5.0)
        
        # Create undercut region objects
        results = []
        for region_indices in undercut_regions:
            # Compute severity based on angle
            region_angles = angles_deg[region_indices]
            severity = np.mean((region_angles - 90.0) / 90.0)  # 0-1 scale
            
            # Determine issue level
            if severity > 0.5:
                issue_level = IssueLevel.CRITICAL
            elif severity > 0.2:
                issue_level = IssueLevel.WARNING
            else:
                issue_level = IssueLevel.ACCEPTABLE
            
            results.append(UndercutRegion(
                vertex_indices=region_indices.tolist(),
                severity=float(severity),
                draft_direction=draft_direction,
                issue_level=issue_level
            ))
        
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.success(f"Undercut detection complete ({elapsed:.2f}ms): {len(results)} regions found")
        
        return results
    
    def detect_sharp_edges(
        self,
        mesh: o3d.geometry.TriangleMesh
    ) -> List[SharpEdge]:
        """
        Detect sharp edges that may need filleting.
        
        Args:
            mesh: Input mesh
            
        Returns:
            List of sharp edges
        """
        start_time = time.perf_counter()
        logger.info("Detecting sharp edges...")
        
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)
        
        # Build edge-to-face map
        edge_faces = {}
        for face_idx, tri in enumerate(triangles):
            edges = [
                tuple(sorted([tri[0], tri[1]])),
                tuple(sorted([tri[1], tri[2]])),
                tuple(sorted([tri[2], tri[0]]))
            ]
            for edge in edges:
                if edge not in edge_faces:
                    edge_faces[edge] = []
                edge_faces[edge].append(face_idx)
        
        # Compute face normals
        mesh.compute_triangle_normals()
        face_normals = np.asarray(mesh.triangle_normals)
        
        sharp_edges = []
        
        # Check each edge
        for edge, face_list in edge_faces.items():
            if len(face_list) == 2:  # Interior edge
                # Compute dihedral angle
                n1 = face_normals[face_list[0]]
                n2 = face_normals[face_list[1]]
                
                dot = np.dot(n1, n2)
                angle = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
                
                # Sharp if angle is small
                if angle < self.sharp_edge_threshold:
                    v1, v2 = edge
                    location = (vertices[v1] + vertices[v2]) / 2
                    
                    sharp_edges.append(SharpEdge(
                        vertex_pairs=[edge],
                        angle=float(angle),
                        location=location
                    ))
        
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.success(f"Sharp edge detection complete ({elapsed:.2f}ms): {len(sharp_edges)} edges found")
        
        return sharp_edges
    
    def analyze_draft_angles(
        self,
        mesh: o3d.geometry.TriangleMesh,
        draft_direction: np.ndarray = np.array([0, 0, 1])
    ) -> np.ndarray:
        """
        Analyze draft angles for each face.
        
        Args:
            mesh: Input mesh
            draft_direction: Mold separation direction
            
        Returns:
            Array of draft angles (degrees) for each face
        """
        mesh.compute_triangle_normals()
        face_normals = np.asarray(mesh.triangle_normals)
        
        # Normalize draft direction
        draft_direction = draft_direction / np.linalg.norm(draft_direction)
        
        # Compute angles
        dot_products = np.dot(face_normals, draft_direction)
        angles = np.arccos(np.clip(dot_products, -1.0, 1.0))
        draft_angles = 90.0 - np.degrees(angles)  # 0° = parallel, 90° = perpendicular
        
        return draft_angles
    
    def generate_report(self, mesh: o3d.geometry.TriangleMesh) -> ManufacturabilityReport:
        """
        Generate comprehensive manufacturability report.
        
        Args:
            mesh: Input mesh
            
        Returns:
            Complete analysis report
        """
        logger.info("Generating manufacturability report...")
        
        # Run all analyses
        thickness = self.analyze_wall_thickness(mesh)
        undercuts = self.detect_undercuts(mesh)
        sharp_edges = self.detect_sharp_edges(mesh)
        draft_angles = self.analyze_draft_angles(mesh)
        
        # Compute overall score (0-100)
        score = 100.0
        
        # Penalize thin walls
        if thickness.min_thickness < self.min_wall_thickness:
            score -= 20 * (1 - thickness.min_thickness / self.min_wall_thickness)
        
        # Penalize undercuts
        critical_undercuts = sum(1 for u in undercuts if u.issue_level == IssueLevel.CRITICAL)
        score -= min(30, critical_undercuts * 10)
        
        # Penalize sharp edges
        score -= min(20, len(sharp_edges) * 0.5)
        
        # Penalize insufficient draft
        insufficient_draft = np.sum(draft_angles < self.min_draft_angle)
        score -= min(15, insufficient_draft / len(draft_angles) * 100)
        
        score = max(0.0, score)
        
        # Summary
        issues_summary = {
            "thin_walls": len(thickness.thin_regions),
            "undercuts_critical": sum(1 for u in undercuts if u.issue_level == IssueLevel.CRITICAL),
            "undercuts_warning": sum(1 for u in undercuts if u.issue_level == IssueLevel.WARNING),
            "sharp_edges": len(sharp_edges),
            "insufficient_draft": int(insufficient_draft)
        }
        
        logger.success(f"Manufacturability score: {score:.1f}/100")
        
        return ManufacturabilityReport(
            thickness=thickness,
            undercuts=undercuts,
            sharp_edges=sharp_edges,
            draft_angles=draft_angles,
            overall_score=score,
            issues_summary=issues_summary
        )
    
    # Helper methods
    
    def _rotate_vector(self, vector: np.ndarray, angle: float) -> np.ndarray:
        """Rotate vector around arbitrary axis by angle (radians)"""
        # Simple rotation around a perpendicular axis
        perp = np.array([-vector[1], vector[0], 0])
        if np.linalg.norm(perp) < 1e-6:
            perp = np.array([1, 0, 0])
        perp = perp / np.linalg.norm(perp)
        
        # Rodrigues rotation
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        return (
            vector * cos_a +
            np.cross(perp, vector) * sin_a +
            perp * np.dot(perp, vector) * (1 - cos_a)
        )
    
    def _cluster_vertices(
        self,
        vertices: np.ndarray,
        indices: np.ndarray,
        threshold: float = 5.0
    ) -> List[np.ndarray]:
        """
        Cluster nearby vertices using distance threshold.
        Simple connected component approach.
        """
        if len(indices) == 0:
            return []
        
        points = vertices[indices]
        
        # Build adjacency using distance threshold
        from scipy.spatial.distance import cdist
        distances = cdist(points, points)
        adjacency = distances < threshold
        
        # Find connected components
        visited = np.zeros(len(indices), dtype=bool)
        clusters = []
        
        for i in range(len(indices)):
            if visited[i]:
                continue
            
            # BFS to find cluster
            cluster = [i]
            queue = [i]
            visited[i] = True
            
            while queue:
                current = queue.pop(0)
                neighbors = np.where(adjacency[current] & ~visited)[0]
                for neighbor in neighbors:
                    visited[neighbor] = True
                    cluster.append(neighbor)
                    queue.append(neighbor)
            
            clusters.append(indices[cluster])
        
        return clusters


def main():
    """Test feature detector"""
    detector = FeatureDetector(
        min_wall_thickness=2.0,
        min_draft_angle=3.0,
        sharp_edge_threshold=30.0
    )
    
    print("FeatureDetector initialized successfully")


if __name__ == "__main__":
    main()
