'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { BoundingBox } from '@/lib/api';
import {
  MagnifyingGlassPlusIcon,
  MagnifyingGlassMinusIcon,
  ArrowsPointingOutIcon,
  SunIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';

interface DicomViewerProps {
  imageUrl: string;
  boundingBoxes?: BoundingBox[];
  showOverlay?: boolean;
  onToggleOverlay?: () => void;
}

const WL_PRESETS = [
  { name: 'Default', wc: 127, ww: 255 },
  { name: 'Lung', wc: -600, ww: 1500 },
  { name: 'Mediastinum', wc: 50, ww: 350 },
  { name: 'Bone', wc: 300, ww: 1500 },
];

export default function DicomViewer({
  imageUrl,
  boundingBoxes = [],
  showOverlay = true,
  onToggleOverlay,
}: DicomViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [windowLevel, setWindowLevel] = useState({ wc: 127, ww: 255 });
  const [selectedPreset, setSelectedPreset] = useState('Default');
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });

  // Load image
  useEffect(() => {
    if (!imageUrl) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      setImage(img);
      setImageSize({ width: img.width, height: img.height });
      // Reset view
      setZoom(1);
      setPan({ x: 0, y: 0 });
    };
    img.onerror = (e) => {
      console.error('Failed to load image:', e);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Render canvas
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !image) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to container size
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    // Clear canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Calculate image dimensions to fit container while maintaining aspect ratio
    const containerAspect = canvas.width / canvas.height;
    const imageAspect = image.width / image.height;

    let drawWidth, drawHeight;
    if (imageAspect > containerAspect) {
      drawWidth = canvas.width * zoom;
      drawHeight = (canvas.width / imageAspect) * zoom;
    } else {
      drawHeight = canvas.height * zoom;
      drawWidth = canvas.height * imageAspect * zoom;
    }

    // Center image with pan offset
    const x = (canvas.width - drawWidth) / 2 + pan.x;
    const y = (canvas.height - drawHeight) / 2 + pan.y;

    // Draw image
    ctx.drawImage(image, x, y, drawWidth, drawHeight);

    // Draw bounding boxes if overlay is enabled
    if (showOverlay && boundingBoxes.length > 0) {
      boundingBoxes.forEach((box) => {
        // Convert normalized coordinates to canvas coordinates
        const boxX = x + box.x_min * drawWidth;
        const boxY = y + box.y_min * drawHeight;
        const boxWidth = (box.x_max - box.x_min) * drawWidth;
        const boxHeight = (box.y_max - box.y_min) * drawHeight;

        // Set color based on finding type
        let color = '#22c55e'; // Default green
        if (box.finding_name.toLowerCase().includes('nodule')) {
          color = '#ef4444'; // Red
        } else if (box.finding_name.toLowerCase().includes('mass')) {
          color = '#dc2626'; // Dark red
        } else if (box.finding_name.toLowerCase().includes('pneumothorax')) {
          color = '#f97316'; // Orange
        } else if (box.finding_name.toLowerCase().includes('effusion')) {
          color = '#3b82f6'; // Blue
        }

        // Draw box
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

        // Draw label background
        const label = `${box.finding_name} (${(box.confidence * 100).toFixed(0)}%)`;
        ctx.font = '12px sans-serif';
        const textMetrics = ctx.measureText(label);
        const textHeight = 16;
        const padding = 4;

        ctx.fillStyle = color;
        ctx.fillRect(
          boxX,
          boxY - textHeight - padding,
          textMetrics.width + padding * 2,
          textHeight + padding
        );

        // Draw label text
        ctx.fillStyle = '#fff';
        ctx.fillText(label, boxX + padding, boxY - padding);
      });
    }
  }, [image, zoom, pan, showOverlay, boundingBoxes]);

  // Re-render when dependencies change
  useEffect(() => {
    render();
  }, [render]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => render();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [render]);

  // Mouse handlers for pan
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Zoom handlers
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((prev) => Math.max(0.1, Math.min(10, prev * delta)));
  };

  const zoomIn = () => setZoom((prev) => Math.min(10, prev * 1.2));
  const zoomOut = () => setZoom((prev) => Math.max(0.1, prev / 1.2));
  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Window/Level preset handler
  const handlePresetChange = (presetName: string) => {
    const preset = WL_PRESETS.find((p) => p.name === presetName);
    if (preset) {
      setSelectedPreset(presetName);
      setWindowLevel({ wc: preset.wc, ww: preset.ww });
    }
  };

  return (
    <div className="flex flex-col h-full bg-black rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
        <div className="flex items-center space-x-2">
          <button
            onClick={zoomIn}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded"
            title="Zoom In"
          >
            <MagnifyingGlassPlusIcon className="w-5 h-5" />
          </button>
          <button
            onClick={zoomOut}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded"
            title="Zoom Out"
          >
            <MagnifyingGlassMinusIcon className="w-5 h-5" />
          </button>
          <button
            onClick={resetView}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded"
            title="Reset View"
          >
            <ArrowsPointingOutIcon className="w-5 h-5" />
          </button>
          <span className="text-gray-400 text-sm ml-2">
            {(zoom * 100).toFixed(0)}%
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* W/L Presets */}
          <div className="flex items-center space-x-1">
            <SunIcon className="w-4 h-4 text-gray-400" />
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(e.target.value)}
              className="bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border-none"
            >
              {WL_PRESETS.map((preset) => (
                <option key={preset.name} value={preset.name}>
                  {preset.name}
                </option>
              ))}
            </select>
          </div>

          {/* Overlay Toggle */}
          <button
            onClick={onToggleOverlay}
            className={`p-2 rounded ${
              showOverlay
                ? 'text-primary-400 bg-primary-900/50'
                : 'text-gray-300 hover:text-white hover:bg-gray-700'
            }`}
            title={showOverlay ? 'Hide Overlay' : 'Show Overlay'}
          >
            {showOverlay ? (
              <EyeIcon className="w-5 h-5" />
            ) : (
              <EyeSlashIcon className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        className="flex-1 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>

      {/* Metadata bar */}
      {imageSize.width > 0 && (
        <div className="px-4 py-1 bg-gray-800 text-gray-400 text-xs flex justify-between">
          <span>
            Size: {imageSize.width} x {imageSize.height}
          </span>
          <span>
            Boxes: {boundingBoxes.length}
          </span>
        </div>
      )}
    </div>
  );
}
