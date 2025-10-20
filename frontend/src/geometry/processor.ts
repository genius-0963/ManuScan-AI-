/**
 * Geometry Processing in Browser
 * Mesh preprocessing and feature extraction
 */

import * as THREE from 'three';
import type { MeshData, GraphData, ProcessorConfig } from '../types';

export class GeometryProcessor {
  private config: ProcessorConfig;

  constructor(config: ProcessorConfig) {
    this.config = config;
  }

  /**
   * Process geometry: clean, decimate, compute features
   */
  async process(geometry: THREE.BufferGeometry): Promise<MeshData> {
    console.log('Processing geometry...');
    const startTime = performance.now();

    // Compute normals if not present
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }

    // Decimate if too large
    if (geometry.attributes.position.count > this.config.maxVertices) {
      console.log(
        `Decimating from ${geometry.attributes.position.count} to ~${this.config.targetVertices} vertices`
      );
      geometry = this.decimate(geometry);
    }

    // Extract mesh data
    const meshData = this.extractMeshData(geometry);

    const elapsed = performance.now() - startTime;
    console.log(`✓ Geometry processed in ${elapsed.toFixed(2)}ms`);

    return meshData;
  }

  /**
   * Extract mesh data from Three.js geometry
   */
  private extractMeshData(geometry: THREE.BufferGeometry): MeshData {
    const positions = geometry.attributes.position.array as Float32Array;
    const normals = geometry.attributes.normal.array as Float32Array;
    const indices = geometry.index?.array;

    const numVertices = positions.length / 3;

    // Convert to vertex array
    const vertices: number[][] = [];
    for (let i = 0; i < numVertices; i++) {
      vertices.push([positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]]);
    }

    // Convert to face array
    const faces: number[][] = [];
    if (indices) {
      for (let i = 0; i < indices.length; i += 3) {
        faces.push([indices[i], indices[i + 1], indices[i + 2]]);
      }
    } else {
      // Non-indexed geometry
      for (let i = 0; i < numVertices; i += 3) {
        faces.push([i, i + 1, i + 2]);
      }
    }

    return {
      vertices,
      normals: Array.from(normals),
      faces,
      geometry,
    };
  }

  /**
   * Simple mesh decimation (placeholder - use real decimation in production)
   */
  private decimate(geometry: THREE.BufferGeometry): THREE.BufferGeometry {
    // Simplified decimation: sample vertices
    // In production, use proper decimation algorithm
    const ratio = this.config.targetVertices / geometry.attributes.position.count;

    if (ratio >= 1) return geometry;

    // This is a placeholder - real implementation would use
    // proper mesh simplification algorithms
    console.warn('Using simplified decimation. Consider implementing proper algorithm.');

    return geometry;
  }

  /**
   * Extract features for GNN input
   */
  extractFeatures(meshData: MeshData): GraphData {
    console.log('Extracting graph features...');

    const numNodes = meshData.vertices.length;

    // Node features: [x, y, z, nx, ny, nz]
    const nodeFeatures: number[][] = [];
    for (let i = 0; i < numNodes; i++) {
      const vertex = meshData.vertices[i];
      const normal = [
        meshData.normals[i * 3],
        meshData.normals[i * 3 + 1],
        meshData.normals[i * 3 + 2],
      ];
      nodeFeatures.push([...vertex, ...normal]);
    }

    // Normalize positions
    const { center, scale } = this.computeNormalization(meshData.vertices);
    for (let i = 0; i < numNodes; i++) {
      nodeFeatures[i][0] = (nodeFeatures[i][0] - center[0]) / scale;
      nodeFeatures[i][1] = (nodeFeatures[i][1] - center[1]) / scale;
      nodeFeatures[i][2] = (nodeFeatures[i][2] - center[2]) / scale;
    }

    // Extract edges from faces
    const edgeSet = new Set<string>();
    const edges: [number, number][] = [];

    for (const face of meshData.faces) {
      // Add edges (both directions for undirected graph)
      const edgePairs = [
        [face[0], face[1]],
        [face[1], face[2]],
        [face[2], face[0]],
        [face[1], face[0]],
        [face[2], face[1]],
        [face[0], face[2]],
      ];

      for (const [v1, v2] of edgePairs) {
        const key = `${v1},${v2}`;
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          edges.push([v1, v2]);
        }
      }
    }

    console.log(`✓ Extracted ${numNodes} nodes, ${edges.length} edges`);

    return {
      nodeFeatures: nodeFeatures.flat(),
      edgeIndex: edges.flat(),
      numNodes,
      numEdges: edges.length,
      featureDim: 6,
    };
  }

  /**
   * Compute normalization parameters
   */
  private computeNormalization(vertices: number[][]): { center: number[]; scale: number } {
    const center = [0, 0, 0];
    for (const v of vertices) {
      center[0] += v[0];
      center[1] += v[1];
      center[2] += v[2];
    }
    center[0] /= vertices.length;
    center[1] /= vertices.length;
    center[2] /= vertices.length;

    let maxDist = 0;
    for (const v of vertices) {
      const dx = v[0] - center[0];
      const dy = v[1] - center[1];
      const dz = v[2] - center[2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (dist > maxDist) maxDist = dist;
    }

    return { center, scale: maxDist };
  }
}

export default GeometryProcessor;
