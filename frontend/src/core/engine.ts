/**
 * ManuScan AI Engine
 * Main analysis engine coordinating loading, inference, and visualization
 */

import * as tf from '@tensorflow/tfjs';
import { STLLoader } from './loader';
import { GeometryProcessor } from '../geometry/processor';
import { InferenceEngine } from './inference';
import type { AnalysisResult, MeshData, EngineConfig } from '../types';

export class ManuScanEngine {
  private stlLoader: STLLoader;
  private geometryProcessor: GeometryProcessor;
  private inferenceEngine: InferenceEngine;
  private config: EngineConfig;
  private currentMesh: MeshData | null = null;

  constructor(config: Partial<EngineConfig> = {}) {
    this.config = {
      useWebGL: true,
      useWasm: true,
      modelPath: '/models/manuscan_model.json',
      maxVertices: 500000,
      targetVertices: 100000,
      ...config,
    };

    this.stlLoader = new STLLoader();
    this.geometryProcessor = new GeometryProcessor({
      maxVertices: this.config.maxVertices,
      targetVertices: this.config.targetVertices,
    });
    this.inferenceEngine = new InferenceEngine(this.config.modelPath);
  }

  /**
   * Initialize the engine and load models
   */
  async initialize(): Promise<void> {
    console.log('Initializing ManuScan AI Engine...');
    const startTime = performance.now();

    // Set TensorFlow.js backend
    if (this.config.useWebGL) {
      await tf.setBackend('webgl');
      console.log('✓ WebGL backend enabled');
    } else {
      await tf.setBackend('cpu');
      console.log('⚠ Using CPU backend');
    }

    await tf.ready();

    // Load inference model
    await this.inferenceEngine.loadModel();

    const elapsed = performance.now() - startTime;
    console.log(`✓ Engine initialized in ${elapsed.toFixed(2)}ms`);
  }

  /**
   * Load 3D model from file
   */
  async loadModel(file: File | string): Promise<void> {
    console.log('Loading 3D model...');
    const startTime = performance.now();

    let geometry;
    if (typeof file === 'string') {
      geometry = await this.stlLoader.loadFromUrl(file);
    } else {
      geometry = await this.stlLoader.loadFromFile(file);
    }

    // Process geometry
    this.currentMesh = await this.geometryProcessor.process(geometry);

    const elapsed = performance.now() - startTime;
    console.log(
      `✓ Model loaded: ${this.currentMesh.vertices.length} vertices, ${this.currentMesh.faces.length} faces (${elapsed.toFixed(2)}ms)`
    );
  }

  /**
   * Run complete manufacturability analysis
   */
  async analyze(): Promise<AnalysisResult> {
    if (!this.currentMesh) {
      throw new Error('No model loaded. Call loadModel() first.');
    }

    console.log('Running manufacturability analysis...');
    const startTime = performance.now();

    // Extract features from mesh
    const features = this.geometryProcessor.extractFeatures(this.currentMesh);

    // Run AI inference
    const predictions = await this.inferenceEngine.predict(features);

    // Post-process results
    const result: AnalysisResult = {
      thickness: {
        min: predictions.thickness.min,
        max: predictions.thickness.max,
        mean: predictions.thickness.mean,
        map: predictions.thickness.map,
        thinRegions: this.findThinRegions(predictions.thickness.map, 2.0), // 2mm threshold
      },
      undercuts: {
        detected: predictions.undercuts.count > 0,
        regions: predictions.undercuts.regions,
        severity: predictions.undercuts.severity,
      },
      sharpEdges: {
        count: predictions.sharpEdges.count,
        locations: predictions.sharpEdges.locations,
      },
      draftAngles: {
        map: predictions.draftAngles,
        insufficientCount: this.countInsufficientDraft(predictions.draftAngles, 3.0),
      },
      overallScore: predictions.overallScore * 100, // 0-100 scale
      timestamp: new Date(),
      processingTime: 0, // Will be set below
    };

    const elapsed = performance.now() - startTime;
    result.processingTime = elapsed;

    console.log(`✓ Analysis complete in ${elapsed.toFixed(2)}ms`);
    console.log(`  Manufacturability Score: ${result.overallScore.toFixed(1)}/100`);
    console.log(`  Thin walls: ${result.thickness.thinRegions.length}`);
    console.log(`  Undercuts: ${result.undercuts.regions.length}`);
    console.log(`  Sharp edges: ${result.sharpEdges.count}`);

    return result;
  }

  /**
   * Get current mesh data for visualization
   */
  getMeshData(): MeshData | null {
    return this.currentMesh;
  }

  /**
   * Generate heatmap colors for visualization
   */
  generateHeatmap(values: Float32Array, min: number, max: number): Float32Array {
    const colors = new Float32Array(values.length * 3);

    for (let i = 0; i < values.length; i++) {
      const normalized = (values[i] - min) / (max - min);
      const color = this.valueToColor(normalized);
      colors[i * 3] = color[0];
      colors[i * 3 + 1] = color[1];
      colors[i * 3 + 2] = color[2];
    }

    return colors;
  }

  /**
   * Convert normalized value to RGB color (red-yellow-green gradient)
   */
  private valueToColor(value: number): [number, number, number] {
    // Clamp value to [0, 1]
    value = Math.max(0, Math.min(1, value));

    let r, g, b;

    if (value < 0.5) {
      // Red to Yellow
      r = 1;
      g = value * 2;
      b = 0;
    } else {
      // Yellow to Green
      r = 1 - (value - 0.5) * 2;
      g = 1;
      b = 0;
    }

    return [r, g, b];
  }

  /**
   * Find regions with thickness below threshold
   */
  private findThinRegions(thicknessMap: Float32Array, threshold: number): number[] {
    const regions: number[] = [];

    for (let i = 0; i < thicknessMap.length; i++) {
      if (thicknessMap[i] > 0 && thicknessMap[i] < threshold) {
        regions.push(i);
      }
    }

    return regions;
  }

  /**
   * Count faces with insufficient draft angle
   */
  private countInsufficientDraft(draftAngles: Float32Array, minAngle: number): number {
    let count = 0;
    for (let i = 0; i < draftAngles.length; i++) {
      if (draftAngles[i] < minAngle) {
        count++;
      }
    }
    return count;
  }

  /**
   * Export analysis report as JSON
   */
  exportJSON(result: AnalysisResult): string {
    return JSON.stringify(result, null, 2);
  }

  /**
   * Cleanup resources
   */
  dispose(): void {
    this.inferenceEngine.dispose();
    tf.disposeVariables();
    console.log('✓ Engine resources disposed');
  }
}

export default ManuScanEngine;
