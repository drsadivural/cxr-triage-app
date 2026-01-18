'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import apiClient, { AnalysisResult } from '@/lib/api';
import DicomViewer from '@/components/DicomViewer';
import FindingsPanel from '@/components/FindingsPanel';
import {
  ArrowLeftIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
  PhotoIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline';

export default function StudyDetailPage() {
  const params = useParams();
  const studyId = params.id as string;
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [showOverlay, setShowOverlay] = useState(true);

  useEffect(() => {
    const fetchStudy = async () => {
      try {
        const data = await apiClient.getResult(studyId);
        setResult(data);
      } catch (error) {
        console.error('Failed to fetch study:', error);
        toast.error('Failed to load study');
      } finally {
        setLoading(false);
      }
    };

    fetchStudy();
  }, [studyId]);

  const handleExport = async (format: 'json' | 'png' | 'dicom_sr') => {
    try {
      const data = await apiClient.exportStudy(studyId, format);

      if (format === 'json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: 'application/json',
        });
        downloadBlob(blob, `result_${studyId}.json`);
      } else {
        downloadBlob(data, `${format}_${studyId}.${format === 'png' ? 'png' : 'dcm'}`);
      }

      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (error) {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 spinner" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Study not found</p>
        <Link href="/worklist" className="text-primary-600 hover:underline mt-4 inline-block">
          Back to Worklist
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <Link
            href="/worklist"
            className="mr-4 p-2 hover:bg-gray-100 rounded-md"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-600" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Study Details</h1>
            <p className="text-sm text-gray-500">{studyId}</p>
          </div>
        </div>
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
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        {/* Left: Viewer */}
        <div className="lg:col-span-2 min-h-0">
          <DicomViewer
            imageUrl={apiClient.getImageUrl(studyId)}
            boundingBoxes={result.bounding_boxes}
            showOverlay={showOverlay}
            onToggleOverlay={() => setShowOverlay(!showOverlay)}
          />
        </div>

        {/* Right: Results Panel */}
        <div className="overflow-y-auto">
          <FindingsPanel
            findings={result.findings}
            boundingBoxes={result.bounding_boxes}
            triageLevel={result.triage_level}
            triageReasons={result.triage_reasons}
            report={result.report}
            processingTimeMs={result.processing_time_ms}
            modelInfo={result.model_info}
          />
        </div>
      </div>
    </div>
  );
}
