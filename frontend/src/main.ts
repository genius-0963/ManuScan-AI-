/**
 * ManuScan AI - Main Application Entry
 */

import { ManuScanEngine } from './core/engine';
import { ModelViewer } from './visualization/viewer';
import { VisualizationMode } from './types';
import type { AnalysisResult } from './types';
import './styles/main.css';

class ManuScanApp {
  private engine: ManuScanEngine;
  private viewer: ModelViewer | null = null;
  private currentResult: AnalysisResult | null = null;

  constructor() {
    this.engine = new ManuScanEngine({
      useWebGL: true,
      useWasm: true,
      modelPath: '/models/manuscan_model.json',
      maxVertices: 500000,
      targetVertices: 100000,
    });

    this.setupUI();
  }

  async initialize(): Promise<void> {
    console.log('🚀 Initializing ManuScan AI...');
    const startTime = performance.now();

    try {
      // Initialize engine
      await this.engine.initialize();

      // Initialize viewer
      const viewerContainer = document.getElementById('viewer-container');
      if (!viewerContainer) {
        throw new Error('Viewer container not found');
      }

      this.viewer = new ModelViewer({
        container: viewerContainer,
        backgroundColor: 0x2a2a2a,
        enableControls: true,
        enableGrid: false,
      });

      const elapsed = performance.now() - startTime;
      console.log(`✅ ManuScan AI ready (${elapsed.toFixed(2)}ms)`);

      this.showStatus('Ready to analyze', 'success');
    } catch (error) {
      console.error('Initialization failed:', error);
      this.showStatus('Initialization failed', 'error');
    }
  }

  private setupUI(): void {
    // File upload
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    fileInput?.addEventListener('change', this.handleFileUpload.bind(this));

    // Upload button
    const uploadBtn = document.getElementById('upload-btn');
    uploadBtn?.addEventListener('click', () => fileInput?.click());

    // Demo button
    const demoBtn = document.getElementById('demo-btn');
    demoBtn?.addEventListener('click', this.loadDemoAnalysis.bind(this));

    // Analyze button
    const analyzeBtn = document.getElementById('analyze-btn');
    analyzeBtn?.addEventListener('click', this.runAnalysis.bind(this));

    // Visualization mode selector
    const modeSelector = document.getElementById('viz-mode') as HTMLSelectElement;
    modeSelector?.addEventListener('change', this.changeVisualizationMode.bind(this));

    // Export button
    const exportBtn = document.getElementById('export-btn');
    exportBtn?.addEventListener('click', this.exportResults.bind(this));
  }

  private async handleFileUpload(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) return;

    this.showStatus('Loading model...', 'loading');

    try {
      await this.engine.loadModel(file);

      // Display mesh in viewer
      const meshData = this.engine.getMeshData();
      if (meshData && this.viewer) {
        this.viewer.loadMesh(meshData);
      }

      this.showStatus('Model loaded. Click Analyze to start.', 'success');

      // Enable analyze button
      const analyzeBtn = document.getElementById('analyze-btn') as HTMLButtonElement;
      if (analyzeBtn) analyzeBtn.disabled = false;
    } catch (error) {
      console.error('Failed to load model:', error);
      this.showStatus('Failed to load model', 'error');
    }
  }

  private async runAnalysis(): Promise<void> {
    this.showStatus('Analyzing manufacturability...', 'loading');

    try {
      const result = await this.engine.analyze();
      this.currentResult = result;

      // Display results
      this.displayResults(result);

      // Apply default visualization
      this.visualizeThickness();

      this.showStatus(
        `Analysis complete - Score: ${result.overallScore.toFixed(1)}/100`,
        'success'
      );
    } catch (error) {
      console.error('Analysis failed:', error);
      this.showStatus('Analysis failed', 'error');
    }
  }

  private displayResults(result: AnalysisResult): void {
    // Update score
    const scoreEl = document.getElementById('overall-score');
    if (scoreEl) {
      scoreEl.textContent = result.overallScore.toFixed(1);
      scoreEl.className = `score ${this.getScoreClass(result.overallScore)}`;
    }

    // Update metrics
    this.updateMetric('min-thickness', `${result.thickness.min.toFixed(2)} mm`);
    this.updateMetric('thin-walls', `${result.thickness.thinRegions.length}`);
    this.updateMetric('undercuts', `${result.undercuts.regions.length}`);
    this.updateMetric('sharp-edges', `${result.sharpEdges.count}`);
    this.updateMetric('processing-time', `${result.processingTime.toFixed(2)} ms`);

    // Update verdict
    this.updateVerdict(result);

    // Show results panel
    const resultsPanel = document.getElementById('results-panel');
    if (resultsPanel) resultsPanel.style.display = 'block';
  }

  private updateVerdict(result: AnalysisResult): void {
    const verdictText = document.getElementById('verdict-text');
    const verdictSection = document.getElementById('verdict-section');
    
    if (!verdictText || !verdictSection) return;

    let verdict = '';
    let bgColor = '';
    let borderColor = '';
    let textColor = '';
    let icon = '';

    if (result.overallScore >= 80) {
      icon = '✅';
      verdict = 'Excellent manufacturability! Part is ready for production.';
      bgColor = 'rgba(0, 150, 0, 0.1)';
      borderColor = 'rgba(0, 150, 0, 0.3)';
      textColor = '#00aa00';
    } else if (result.overallScore >= 60) {
      icon = '⚠️';
      verdict = `Good manufacturability with ${result.thickness.thinRegions.length} thin regions and ${result.sharpEdges.count} sharp edges. Minor revisions recommended.`;
      bgColor = 'rgba(255, 165, 0, 0.1)';
      borderColor = 'rgba(255, 165, 0, 0.3)';
      textColor = '#ff8800';
    } else {
      icon = '❌';
      verdict = 'Multiple manufacturability issues detected. Significant design revisions required.';
      bgColor = 'rgba(200, 0, 0, 0.1)';
      borderColor = 'rgba(200, 0, 0, 0.3)';
      textColor = '#cc0000';
    }

    verdictSection.style.background = bgColor;
    verdictSection.style.border = `2px solid ${borderColor}`;
    const header = verdictSection.querySelector('h3');
    if (header) {
      header.textContent = `${icon} Manufacturing Verdict`;
      (header as HTMLElement).style.color = textColor;
    }
    verdictText.textContent = verdict;
  }

  private updateMetric(id: string, value: string): void {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  private getScoreClass(score: number): string {
    if (score >= 80) return 'good';
    if (score >= 60) return 'warning';
    return 'critical';
  }

  private changeVisualizationMode(event: Event): void {
    if (!this.currentResult || !this.viewer) return;

    const mode = (event.target as HTMLSelectElement).value as VisualizationMode;

    switch (mode) {
      case VisualizationMode.Thickness:
        this.visualizeThickness();
        break;
      case VisualizationMode.Undercuts:
        this.visualizeUndercuts();
        break;
      case VisualizationMode.SharpEdges:
        this.visualizeSharpEdges();
        break;
      case VisualizationMode.Normal:
      default:
        this.viewer.resetColors();
        break;
    }
  }

  private visualizeThickness(): void {
    if (!this.currentResult || !this.viewer) return;

    const { thickness } = this.currentResult;

    this.viewer.applyHeatmap(thickness.map, {
      colormap: 'redyellowgreen',
      min: thickness.min,
      max: thickness.max,
    });
  }

  private visualizeUndercuts(): void {
    if (!this.currentResult || !this.viewer) return;

    this.viewer.resetColors();
    this.viewer.highlightRegions(this.currentResult.undercuts.regions);
  }

  private visualizeSharpEdges(): void {
    if (!this.currentResult || !this.viewer) return;

    this.viewer.resetColors();
    this.viewer.highlightRegions(this.currentResult.sharpEdges.locations);
  }

  private exportResults(): void {
    if (!this.currentResult) {
      alert('No analysis results to export');
      return;
    }

    const json = this.engine.exportJSON(this.currentResult);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `manuscan-analysis-${Date.now()}.json`;
    a.click();

    URL.revokeObjectURL(url);

    this.showStatus('Results exported', 'success');
  }

  private loadDemoAnalysis(): void {
    this.showStatus('Loading demo analysis...', 'loading');

    // Create thickness map with variation
    const thicknessMap = new Float32Array(50000);
    for (let i = 0; i < thicknessMap.length; i++) {
      const variation = Math.sin(i / 1000) * 3 + Math.cos(i / 500) * 2;
      thicknessMap[i] = Math.max(2.0, 6.2 + variation);
    }

    // Create demo analysis result matching the types
    const demoResult: AnalysisResult = {
      overallScore: 87.0,
      thickness: {
        min: 2.3,
        max: 15.8,
        mean: 6.2,
        thinRegions: [12453, 23891, 34567], // Thin wall vertex indices
        map: thicknessMap
      },
      undercuts: {
        detected: false,
        regions: [], // No undercuts in this demo
        severity: 0
      },
      sharpEdges: {
        count: 8,
        locations: [4521, 4522, 8932, 8933, 15234, 15235, 20123, 20124] // Sharp edge vertex indices
      },
      draftAngles: {
        map: new Float32Array(50000).fill(15.3),
        insufficientCount: 12
      },
      processingTime: 1234.5,
      timestamp: new Date()
    };

    this.currentResult = demoResult;
    this.displayResults(demoResult);

    this.showStatus('Demo analysis loaded - Score: 87.0/100', 'success');
  }

  private showStatus(message: string, type: 'loading' | 'success' | 'error'): void {
    const statusEl = document.getElementById('status-message');
    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = `status ${type}`;

    if (type !== 'loading') {
      setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = 'status';
      }, 3000);
    }
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  const app = new ManuScanApp();
  await app.initialize();
});

export default ManuScanApp;
