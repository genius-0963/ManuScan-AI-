"""
Performance Benchmarking Script
Tests and measures ManuScan AI performance
"""

import time
import numpy as np
from pathlib import Path
import torch
from loguru import logger
import pandas as pd
from typing import Dict, List

from backend.geometry.mesh_processor import MeshProcessor
from backend.geometry.feature_detection import FeatureDetector
from backend.geometry.graph_converter import MeshToGraphConverter
from backend.models.gnn_architecture import create_model


class PerformanceBenchmark:
    """
    Comprehensive performance benchmark suite.
    """
    
    def __init__(self):
        self.results = []
        self.mesh_processor = MeshProcessor(use_gpu=True, target_vertices=100000)
        self.feature_detector = FeatureDetector()
        self.graph_converter = MeshToGraphConverter()
        
    def benchmark_mesh_loading(self, file_path: str, num_runs: int = 10) -> Dict:
        """Benchmark mesh loading performance"""
        logger.info(f"Benchmarking mesh loading ({num_runs} runs)...")
        
        times = []
        for i in range(num_runs):
            start = time.perf_counter()
            mesh = self.mesh_processor.load_mesh(file_path)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return {
            'operation': 'Mesh Loading',
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def benchmark_preprocessing(self, file_path: str, num_runs: int = 10) -> Dict:
        """Benchmark mesh preprocessing"""
        logger.info(f"Benchmarking preprocessing ({num_runs} runs)...")
        
        mesh = self.mesh_processor.load_mesh(file_path)
        
        times = []
        for i in range(num_runs):
            # Make a copy to avoid modifying original
            mesh_copy = mesh
            
            start = time.perf_counter()
            processed = self.mesh_processor.preprocess(mesh_copy)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return {
            'operation': 'Preprocessing',
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def benchmark_thickness_analysis(self, file_path: str, num_runs: int = 5) -> Dict:
        """Benchmark wall thickness analysis"""
        logger.info(f"Benchmarking thickness analysis ({num_runs} runs)...")
        
        mesh = self.mesh_processor.load_mesh(file_path)
        mesh = self.mesh_processor.preprocess(mesh)
        
        times = []
        for i in range(num_runs):
            start = time.perf_counter()
            result = self.feature_detector.analyze_wall_thickness(mesh)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return {
            'operation': 'Thickness Analysis',
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def benchmark_undercut_detection(self, file_path: str, num_runs: int = 5) -> Dict:
        """Benchmark undercut detection"""
        logger.info(f"Benchmarking undercut detection ({num_runs} runs)...")
        
        mesh = self.mesh_processor.load_mesh(file_path)
        mesh = self.mesh_processor.preprocess(mesh)
        
        times = []
        for i in range(num_runs):
            start = time.perf_counter()
            result = self.feature_detector.detect_undercuts(mesh)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return {
            'operation': 'Undercut Detection',
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def benchmark_graph_conversion(self, file_path: str, num_runs: int = 10) -> Dict:
        """Benchmark graph conversion"""
        logger.info(f"Benchmarking graph conversion ({num_runs} runs)...")
        
        mesh = self.mesh_processor.load_mesh(file_path)
        mesh = self.mesh_processor.preprocess(mesh)
        
        times = []
        for i in range(num_runs):
            start = time.perf_counter()
            graph = self.graph_converter.convert(mesh)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return {
            'operation': 'Graph Conversion',
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def benchmark_inference(self, file_path: str, num_runs: int = 10) -> Dict:
        """Benchmark model inference"""
        logger.info(f"Benchmarking inference ({num_runs} runs)...")
        
        # Load and prepare data
        mesh = self.mesh_processor.load_mesh(file_path)
        mesh = self.mesh_processor.preprocess(mesh)
        graph = self.graph_converter.convert(mesh)
        
        # Create model
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = create_model('gcn', in_channels=6, hidden_channels=128, num_layers=4)
        model = model.to(device)
        model.eval()
        
        # Move data to device
        x = graph.x.to(device)
        edge_index = graph.edge_index.to(device)
        
        # Warmup
        with torch.no_grad():
            for _ in range(3):
                _ = model(x, edge_index)
        
        # Benchmark
        times = []
        with torch.no_grad():
            for i in range(num_runs):
                torch.cuda.synchronize() if torch.cuda.is_available() else None
                
                start = time.perf_counter()
                output = model(x, edge_index)
                torch.cuda.synchronize() if torch.cuda.is_available() else None
                
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
        
        return {
            'operation': 'Model Inference',
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def run_full_benchmark(self, file_path: str) -> pd.DataFrame:
        """Run complete benchmark suite"""
        logger.info("=" * 60)
        logger.info("ManuScan AI - Performance Benchmark")
        logger.info("=" * 60)
        
        benchmarks = [
            self.benchmark_mesh_loading,
            self.benchmark_preprocessing,
            self.benchmark_thickness_analysis,
            self.benchmark_undercut_detection,
            self.benchmark_graph_conversion,
            self.benchmark_inference
        ]
        
        results = []
        for benchmark_func in benchmarks:
            try:
                result = benchmark_func(file_path)
                results.append(result)
                logger.info(
                    f"{result['operation']:.<30} "
                    f"{result['mean_ms']:>8.2f}ms ± {result['std_ms']:>6.2f}ms"
                )
            except Exception as e:
                logger.error(f"Benchmark failed: {e}")
        
        df = pd.DataFrame(results)
        
        # Calculate total pipeline time
        total_time = df['mean_ms'].sum()
        logger.info("=" * 60)
        logger.info(f"Total Pipeline Time: {total_time:.2f}ms")
        logger.info("=" * 60)
        
        # Check if target is met
        if total_time < 100:
            logger.success(f"✅ Target met! ({total_time:.2f}ms < 100ms)")
        else:
            logger.warning(f"⚠️  Target missed ({total_time:.2f}ms > 100ms)")
        
        return df
    
    def save_results(self, df: pd.DataFrame, output_path: str = 'benchmark_results.csv'):
        """Save benchmark results"""
        df.to_csv(output_path, index=False)
        logger.info(f"Results saved to: {output_path}")


def main():
    """Main benchmark script"""
    import open3d as o3d
    
    # Create a test mesh if no file provided
    logger.info("Creating test mesh...")
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=10.0, resolution=50)
    test_file = "test_sphere.stl"
    o3d.io.write_triangle_mesh(test_file, mesh)
    
    # Run benchmarks
    benchmark = PerformanceBenchmark()
    results_df = benchmark.run_full_benchmark(test_file)
    
    # Save results
    benchmark.save_results(results_df)
    
    # Display results
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(results_df.to_string(index=False))
    print("=" * 60)
    
    # Cleanup
    Path(test_file).unlink()


if __name__ == "__main__":
    main()
