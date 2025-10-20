/**
 * TensorFlow.js Inference Engine
 * Runs AI model inference in the browser
 */

import * as tf from '@tensorflow/tfjs';
import type { GraphData, InferencePredictions } from '../types';

export class InferenceEngine {
  private model: tf.GraphModel | null = null;
  private modelPath: string;
  private isLoaded: boolean = false;

  constructor(modelPath: string) {
    this.modelPath = modelPath;
  }

  /**
   * Load TensorFlow.js model
   */
  async loadModel(): Promise<void> {
    console.log(`Loading model from ${this.modelPath}...`);
    const startTime = performance.now();

    try {
      this.model = await tf.loadGraphModel(this.modelPath);
      this.isLoaded = true;

      const elapsed = performance.now() - startTime;
      console.log(`✓ Model loaded in ${elapsed.toFixed(2)}ms`);

      // Warm up model with dummy input
      await this.warmup();
    } catch (error) {
      console.error('Failed to load model:', error);
      throw new Error('Model loading failed. Ensure model files are available.');
    }
  }

  /**
   * Warm up model for faster first inference
   */
  private async warmup(): Promise<void> {
    if (!this.model) return;

    console.log('Warming up model...');

    // Create dummy input matching expected shape
    const dummyNodes = tf.randomNormal([100, 6]); // 100 nodes, 6 features
    const dummyEdges = tf.tensor2d(
      Array.from({ length: 200 }, (_, i) => [
        Math.floor(Math.random() * 100),
        Math.floor(Math.random() * 100),
      ]),
      [200, 2],
      'int32'
    );

    try {
      const result = await this.model.executeAsync({
        node_features: dummyNodes,
        edge_index: dummyEdges,
      });

      // Dispose tensors
      tf.dispose([dummyNodes, dummyEdges, result]);

      console.log('✓ Model warmed up');
    } catch (error) {
      console.warn('Warmup failed:', error);
    }
  }

  /**
   * Run inference on mesh graph data
   */
  async predict(graphData: GraphData): Promise<InferencePredictions> {
    if (!this.model || !this.isLoaded) {
      throw new Error('Model not loaded. Call loadModel() first.');
    }

    const startTime = performance.now();

    // Prepare input tensors
    const nodeFeatures = tf.tensor2d(graphData.nodeFeatures, [
      graphData.numNodes,
      graphData.featureDim,
    ]);

    const edgeIndex = tf.tensor2d(graphData.edgeIndex, [graphData.numEdges, 2], 'int32');

    try {
      // Run inference
      const outputs = (await this.model.executeAsync({
        node_features: nodeFeatures,
        edge_index: edgeIndex,
      })) as tf.Tensor[];

      // Parse outputs
      const predictions = await this.parseOutputs(outputs);

      // Cleanup
      tf.dispose([nodeFeatures, edgeIndex, ...outputs]);

      const elapsed = performance.now() - startTime;
      console.log(`✓ Inference completed in ${elapsed.toFixed(2)}ms`);

      return predictions;
    } catch (error) {
      console.error('Inference failed:', error);
      tf.dispose([nodeFeatures, edgeIndex]);
      throw error;
    }
  }

  /**
   * Parse model outputs into structured predictions
   */
  private async parseOutputs(outputs: tf.Tensor[]): Promise<InferencePredictions> {
    // Expected outputs:
    // [0] thickness: [num_nodes, 1]
    // [1] undercut: [num_nodes, 1]
    // [2] sharp_edge: [num_nodes, 1]
    // [3] overall_score: [1, 1]

    const thicknessData = await outputs[0].data();
    const undercutData = await outputs[1].data();
    const sharpEdgeData = await outputs[2].data();
    const overallScore = (await outputs[3].data())[0];

    // Convert to Float32Array
    const thicknessMap = new Float32Array(thicknessData);
    const undercutMap = new Float32Array(undercutData);
    const sharpEdgeMap = new Float32Array(sharpEdgeData);

    // Analyze thickness
    const thicknessStats = this.computeStats(thicknessMap);

    // Find undercut regions
    const undercutRegions = this.findRegions(undercutMap, 0.5); // threshold 0.5

    // Find sharp edges
    const sharpEdgeLocations = this.findRegions(sharpEdgeMap, 0.5);

    // Estimate draft angles (simplified - in production, compute from normals)
    const draftAngles = new Float32Array(thicknessMap.length).fill(5.0);

    return {
      thickness: {
        min: thicknessStats.min,
        max: thicknessStats.max,
        mean: thicknessStats.mean,
        map: thicknessMap,
      },
      undercuts: {
        count: undercutRegions.length,
        regions: undercutRegions,
        severity: this.computeAverageSeverity(undercutMap, undercutRegions),
      },
      sharpEdges: {
        count: sharpEdgeLocations.length,
        locations: sharpEdgeLocations,
      },
      draftAngles: draftAngles,
      overallScore: overallScore,
    };
  }

  /**
   * Compute statistics for a value array
   */
  private computeStats(values: Float32Array): { min: number; max: number; mean: number } {
    let min = Infinity;
    let max = -Infinity;
    let sum = 0;

    for (let i = 0; i < values.length; i++) {
      const val = values[i];
      if (val < min) min = val;
      if (val > max) max = val;
      sum += val;
    }

    return {
      min,
      max,
      mean: sum / values.length,
    };
  }

  /**
   * Find regions where values exceed threshold
   */
  private findRegions(values: Float32Array, threshold: number): number[] {
    const regions: number[] = [];

    for (let i = 0; i < values.length; i++) {
      if (values[i] > threshold) {
        regions.push(i);
      }
    }

    return regions;
  }

  /**
   * Compute average severity for detected regions
   */
  private computeAverageSeverity(values: Float32Array, regions: number[]): number {
    if (regions.length === 0) return 0;

    let sum = 0;
    for (const idx of regions) {
      sum += values[idx];
    }

    return sum / regions.length;
  }

  /**
   * Get model memory usage
   */
  getMemoryUsage(): { numTensors: number; numBytes: number } {
    const memInfo = tf.memory();
    return {
      numTensors: memInfo.numTensors,
      numBytes: memInfo.numBytes,
    };
  }

  /**
   * Dispose model and free memory
   */
  dispose(): void {
    if (this.model) {
      this.model.dispose();
      this.model = null;
      this.isLoaded = false;
      console.log('✓ Model disposed');
    }
  }
}

export default InferenceEngine;
