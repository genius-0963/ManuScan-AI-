/**
 * Type definitions for ManuScan AI
 */

import * as THREE from 'three';

export interface EngineConfig {
  useWebGL: boolean;
  useWasm: boolean;
  modelPath: string;
  maxVertices: number;
  targetVertices: number;
}

export interface ProcessorConfig {
  maxVertices: number;
  targetVertices: number;
}

export interface MeshData {
  vertices: number[][];
  normals: number[];
  faces: number[][];
  geometry: THREE.BufferGeometry;
}

export interface GraphData {
  nodeFeatures: number[];
  edgeIndex: number[];
  numNodes: number;
  numEdges: number;
  featureDim: number;
}

export interface ThicknessAnalysis {
  min: number;
  max: number;
  mean: number;
  map: Float32Array;
  thinRegions: number[];
}

export interface UndercutAnalysis {
  detected: boolean;
  regions: number[];
  severity: number;
}

export interface SharpEdgeAnalysis {
  count: number;
  locations: number[];
}

export interface DraftAngleAnalysis {
  map: Float32Array;
  insufficientCount: number;
}

export interface AnalysisResult {
  thickness: ThicknessAnalysis;
  undercuts: UndercutAnalysis;
  sharpEdges: SharpEdgeAnalysis;
  draftAngles: DraftAngleAnalysis;
  overallScore: number;
  timestamp: Date;
  processingTime: number;
}

export interface InferencePredictions {
  thickness: {
    min: number;
    max: number;
    mean: number;
    map: Float32Array;
  };
  undercuts: {
    count: number;
    regions: number[];
    severity: number;
  };
  sharpEdges: {
    count: number;
    locations: number[];
  };
  draftAngles: Float32Array;
  overallScore: number;
}

export interface ViewerConfig {
  container: HTMLElement;
  width?: number;
  height?: number;
  backgroundColor?: number;
  enableControls?: boolean;
  enableGrid?: boolean;
}

export interface HeatmapConfig {
  colormap: 'redyellowgreen' | 'jet' | 'viridis';
  min: number;
  max: number;
  opacity?: number;
}

export enum VisualizationMode {
  Normal = 'normal',
  Thickness = 'thickness',
  Undercuts = 'undercuts',
  SharpEdges = 'sharp_edges',
  DraftAngles = 'draft_angles',
}

export interface Annotation {
  id: string;
  position: THREE.Vector3;
  text: string;
  type: 'measurement' | 'note' | 'issue';
  visible: boolean;
}

export interface ExportOptions {
  format: 'json' | 'pdf' | 'csv';
  includeVisualization?: boolean;
  includeRecommendations?: boolean;
}
