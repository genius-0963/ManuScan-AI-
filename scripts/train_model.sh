#!/bin/bash

# Training script for ManuScan AI models

set -e

echo "🚀 ManuScan AI - Training Pipeline"
echo "=================================="

# Configuration
MODEL_TYPE="${MODEL_TYPE:-gcn}"
EPOCHS="${EPOCHS:-100}"
BATCH_SIZE="${BATCH_SIZE:-8}"
LEARNING_RATE="${LEARNING_RATE:-0.001}"
DEVICE="${DEVICE:-cuda}"

echo "Configuration:"
echo "  Model Type: $MODEL_TYPE"
echo "  Epochs: $EPOCHS"
echo "  Batch Size: $BATCH_SIZE"
echo "  Learning Rate: $LEARNING_RATE"
echo "  Device: $DEVICE"
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check GPU availability
if [ "$DEVICE" = "cuda" ]; then
    echo "Checking GPU availability..."
    python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"
    echo ""
fi

# Create directories
mkdir -p checkpoints
mkdir -p logs
mkdir -p backend/data

# Run training
echo "Starting training..."
python -m backend.models.training \
    --model-type "$MODEL_TYPE" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --device "$DEVICE"

echo ""
echo "✅ Training complete!"
echo "📊 View logs: tensorboard --logdir=logs"
echo "💾 Checkpoints saved to: checkpoints/"
