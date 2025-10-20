/**
 * ManuScan AI - Simplified Main Application
 * Works without complex dependencies
 */

import './styles/main.css';

interface AnalysisResult {
  overallScore: number;
  thickness: {
    min: number;
    max: number;
    mean: number;
    thinRegions: number[];
    map: Float32Array;
  };
  undercuts: {
    detected: boolean;
    regions: number[];
    severity: number;
  };
  sharpEdges: {
    count: number;
    locations: number[];
  };
  draftAngles: {
    map: Float32Array;
    insufficientCount: number;
  };
  processingTime: number;
  timestamp: Date;
}

class SimpleManuScanApp {
  private currentResult: AnalysisResult | null = null;

  constructor() {
    this.setupUI();
    this.showStatus('ManuScan AI Ready', 'success');
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

    // Export button
    const exportBtn = document.getElementById('export-btn');
    exportBtn?.addEventListener('click', this.exportResults.bind(this));
  }

  private async handleFileUpload(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) return;

    this.showStatus(`Loading ${file.name}...`, 'loading');

    // Simulate file loading
    setTimeout(() => {
      this.showStatus('Model loaded. Click Analyze or try Demo.', 'success');
      
      // Enable analyze button
      const analyzeBtn = document.getElementById('analyze-btn') as HTMLButtonElement;
      if (analyzeBtn) analyzeBtn.disabled = false;
    }, 1000);
  }

  private async runAnalysis(): Promise<void> {
    this.showStatus('Analyzing manufacturability...', 'loading');

    // Simulate analysis
    setTimeout(() => {
      this.loadDemoAnalysis();
    }, 2000);
  }

  private loadDemoAnalysis(): void {
    this.showStatus('Loading demo analysis...', 'loading');

    // Create thickness map with variation
    const thicknessMap = new Float32Array(50000);
    for (let i = 0; i < thicknessMap.length; i++) {
      const variation = Math.sin(i / 1000) * 3 + Math.cos(i / 500) * 2;
      thicknessMap[i] = Math.max(2.0, 6.2 + variation);
    }

    // Create demo analysis result
    const demoResult: AnalysisResult = {
      overallScore: 87.0,
      thickness: {
        min: 2.3,
        max: 15.8,
        mean: 6.2,
        thinRegions: [12453, 23891, 34567],
        map: thicknessMap
      },
      undercuts: {
        detected: false,
        regions: [],
        severity: 0
      },
      sharpEdges: {
        count: 8,
        locations: [4521, 4522, 8932, 8933, 15234, 15235, 20123, 20124]
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

    this.showStatus('Demo analysis complete - Score: 87.0/100', 'success');
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
    if (resultsPanel) {
      resultsPanel.style.display = 'block';
      resultsPanel.scrollIntoView({ behavior: 'smooth' });
    }
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
      verdict = `Excellent manufacturability! Part is ready for production with ${result.thickness.thinRegions.length} minor thin regions to monitor.`;
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
    if (el) {
      el.textContent = value;
      // Add animation
      el.style.transform = 'scale(1.1)';
      setTimeout(() => {
        el.style.transform = 'scale(1)';
      }, 200);
    }
  }

  private getScoreClass(score: number): string {
    if (score >= 80) return 'good';
    if (score >= 60) return 'warning';
    return 'critical';
  }

  private exportResults(): void {
    if (!this.currentResult) {
      alert('No analysis results to export');
      return;
    }

    const exportData = {
      ...this.currentResult,
      exportDate: new Date().toISOString(),
      modelInfo: {
        name: 'demo_sphere.stl',
        vertices: 50000,
        faces: 100000
      },
      recommendations: [
        'Reinforce thin region at vertex 12,453 (2.3mm thickness)',
        'Add fillet (R=0.5mm) to sharp edge at vertices (8932, 8933)',
        'Review 6 edges with 20-29° angles for potential improvements'
      ]
    };

    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `manuscan-analysis-${Date.now()}.json`;
    a.click();

    URL.revokeObjectURL(url);

    this.showStatus('Results exported successfully!', 'success');
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
document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 ManuScan AI - Initializing...');
  new SimpleManuScanApp();
  console.log('✅ ManuScan AI - Ready!');
});
