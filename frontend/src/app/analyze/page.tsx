'use client';

import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import apiClient, { AnalysisResult } from '@/lib/api';
import FileUpload from '@/components/FileUpload';
import DicomViewer from '@/components/DicomViewer';
import FindingsPanel from '@/components/FindingsPanel';
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  PhotoIcon,
  DocumentIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [showOverlay, setShowOverlay] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);
    setResult(null);
    setError(null);
    setIsAnalyzing(true);

    // Create preview URL
    const previewUrl = URL.createObjectURL(selectedFile);
    setImageUrl(previewUrl);

    try {
      const response = await apiClient.analyzeImage(selectedFile);

      if (response.result) {
        setResult(response.result);
        // Update image URL to server-provided one
        setImageUrl(apiClient.getImageUrl(response.study_id));
        toast.success('Analysis complete!');
      } else if (response.status === 'queued') {
        toast.success('Analysis queued. Check worklist for results.');
      }
    } catch (err: any) {
      console.error('Analysis failed:', err);
      const errorMessage = err.message || 'Analysis failed. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const handleExport = async (format: 'json' | 'png' | 'dicom_sr') => {
    if (!result?.study_id) return;

    try {
      const data = await apiClient.exportStudy(result.study_id, format);

      if (format === 'json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: 'application/json',
        });
        downloadBlob(blob, `result_${result.study_id}.json`);
      } else {
        downloadBlob(data, `${format}_${result.study_id}.${format === 'png' ? 'png' : 'dcm'}`);
      }

      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (err) {
      toast.error('Export failed');
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleRetry = () => {
    if (file) {
      handleFileSelect(file);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Analyze Chest X-ray</h1>
        {result && (
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500 mr-2">Export:</span>
            <button
              onClick={() => handleExport('json')}
              className="flex items-center px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <DocumentTextIcon className="w-4 h-4 mr-1" />
              JSON
            </button>
            <button
              onClick={() => handleExport('png')}
              className="flex items-center px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <PhotoIcon className="w-4 h-4 mr-1" />
              PNG
            </button>
            <button
              onClick={() => handleExport('dicom_sr')}
              className="flex items-center px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <DocumentIcon className="w-4 h-4 mr-1" />
              DICOM SR
            </button>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        {/* Left: Viewer */}
        <div className="lg:col-span-2 flex flex-col min-h-0">
          {!file ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="w-full max-w-xl">
                <FileUpload onFileSelect={handleFileSelect} isLoading={isAnalyzing} />
              </div>
            </div>
          ) : (
            <div className="flex-1 min-h-0">
              <DicomViewer
                imageUrl={imageUrl || ''}
                boundingBoxes={result?.bounding_boxes || []}
                showOverlay={showOverlay}
                onToggleOverlay={() => setShowOverlay(!showOverlay)}
              />
            </div>
          )}

          {/* Upload new button when file exists */}
          {file && !isAnalyzing && (
            <div className="mt-4">
              <FileUpload onFileSelect={handleFileSelect} isLoading={isAnalyzing} />
            </div>
          )}
        </div>

        {/* Right: Results Panel */}
        <div className="overflow-y-auto">
          {isAnalyzing ? (
            <div className="card p-8 text-center">
              <div className="w-12 h-12 spinner mx-auto mb-4" />
              <p className="text-gray-600">Analyzing image...</p>
              <p className="text-sm text-gray-400 mt-2">
                This may take a few seconds
              </p>
            </div>
          ) : error ? (
            <div className="card p-6">
              <div className="flex items-start space-x-3">
                <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-red-800">Analysis Failed</h3>
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                  
                  {error.includes('Inference service') && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-sm text-yellow-800">
                        <strong>Tip:</strong> The inference service needs to be running for analysis. 
                        Make sure all Docker containers are started with:
                      </p>
                      <code className="block mt-2 text-xs bg-yellow-100 p-2 rounded">
                        docker-compose up -d
                      </code>
                    </div>
                  )}
                  
                  {error.includes('Cannot connect') && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-sm text-yellow-800">
                        <strong>Tip:</strong> Cannot connect to the backend server. 
                        Please ensure the backend is running on the correct port.
                      </p>
                    </div>
                  )}
                  
                  <button
                    onClick={handleRetry}
                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                  >
                    Retry Analysis
                  </button>
                </div>
              </div>
            </div>
          ) : result ? (
            <FindingsPanel
              findings={result.findings}
              boundingBoxes={result.bounding_boxes}
              triageLevel={result.triage_level}
              triageReasons={result.triage_reasons}
              report={result.report}
              processingTimeMs={result.processing_time_ms}
              modelInfo={result.model_info}
            />
          ) : (
            <div className="card p-8 text-center">
              <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">
                Upload an image to see analysis results
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
