'use client';

import { Finding, BoundingBox, Report } from '@/lib/api';
import clsx from 'clsx';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  QuestionMarkCircleIcon,
  MinusCircleIcon,
} from '@heroicons/react/24/outline';

interface FindingsPanelProps {
  findings: Finding[];
  boundingBoxes: BoundingBox[];
  triageLevel: 'NORMAL' | 'ROUTINE' | 'URGENT' | null;
  triageReasons: string[];
  report: Report | null;
  processingTimeMs: number | null;
  modelInfo: Record<string, any>;
}

const statusConfig = {
  POSITIVE: {
    icon: ExclamationTriangleIcon,
    color: 'text-red-600',
    bg: 'bg-red-100',
    label: 'Positive',
  },
  POSSIBLE: {
    icon: QuestionMarkCircleIcon,
    color: 'text-yellow-600',
    bg: 'bg-yellow-100',
    label: 'Possible',
  },
  UNCERTAIN: {
    icon: QuestionMarkCircleIcon,
    color: 'text-orange-600',
    bg: 'bg-orange-100',
    label: 'Uncertain',
  },
  NEG: {
    icon: CheckCircleIcon,
    color: 'text-gray-500',
    bg: 'bg-gray-100',
    label: 'Negative',
  },
};

const triageConfig = {
  URGENT: {
    color: 'bg-red-100 text-red-800 border-red-200',
    label: 'URGENT',
  },
  ROUTINE: {
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    label: 'ROUTINE',
  },
  NORMAL: {
    color: 'bg-green-100 text-green-800 border-green-200',
    label: 'NORMAL',
  },
};

export default function FindingsPanel({
  findings,
  boundingBoxes,
  triageLevel,
  triageReasons,
  report,
  processingTimeMs,
  modelInfo,
}: FindingsPanelProps) {
  // Sort findings by probability (highest first)
  const sortedFindings = [...findings].sort(
    (a, b) =>
      (b.calibrated_probability || b.probability) -
      (a.calibrated_probability || a.probability)
  );

  return (
    <div className="space-y-4">
      {/* Triage Level */}
      {triageLevel && (
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900">Triage Level</h3>
          </div>
          <div className="card-body">
            <div
              className={clsx(
                'inline-flex items-center px-4 py-2 rounded-full text-lg font-bold border-2',
                triageConfig[triageLevel]?.color
              )}
            >
              {triageConfig[triageLevel]?.label || triageLevel}
            </div>
            {triageReasons.length > 0 && (
              <ul className="mt-3 space-y-1">
                {triageReasons.map((reason, idx) => (
                  <li key={idx} className="text-sm text-gray-600 flex items-start">
                    <span className="mr-2">•</span>
                    {reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Findings Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold text-gray-900">Findings</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Finding
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Probability
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedFindings.map((finding, idx) => {
                const config = statusConfig[finding.status];
                const Icon = config.icon;
                const prob = finding.calibrated_probability || finding.probability;

                return (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-medium text-gray-900 capitalize">
                        {finding.finding_name.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={clsx(
                          'inline-flex items-center px-2 py-1 rounded text-xs font-medium',
                          config.bg,
                          config.color
                        )}
                      >
                        <Icon className="w-4 h-4 mr-1" />
                        {config.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                          <div
                            className={clsx(
                              'h-2 rounded-full',
                              prob >= finding.strong_threshold
                                ? 'bg-red-500'
                                : prob >= finding.triage_threshold
                                ? 'bg-yellow-500'
                                : 'bg-gray-400'
                            )}
                            style={{ width: `${prob * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600">
                          {(prob * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {sortedFindings.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-gray-500">
                    No findings available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bounding Boxes */}
      {boundingBoxes.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900">
              Detected Regions ({boundingBoxes.length})
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-2">
              {boundingBoxes.map((box, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded"
                >
                  <span className="font-medium capitalize">
                    {box.finding_name.replace(/_/g, ' ')}
                  </span>
                  <span className="text-sm text-gray-600">
                    {(box.confidence * 100).toFixed(1)}% confidence
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h3 className="font-semibold text-gray-900">Draft Report</h3>
            {report.llm_rewritten && (
              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                LLM Enhanced
              </span>
            )}
          </div>
          <div className="card-body space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">FINDINGS:</h4>
              <p className="text-gray-600">{report.findings_text}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">IMPRESSION:</h4>
              <p className="text-gray-600">{report.impression_text}</p>
            </div>
            <div className="disclaimer-banner">
              <p className="text-sm text-amber-800">{report.disclaimer}</p>
            </div>
          </div>
        </div>
      )}

      {/* Model Info & Latency */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold text-gray-900">Analysis Info</h3>
        </div>
        <div className="card-body">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {processingTimeMs !== null && (
              <>
                <dt className="text-gray-500">Processing Time</dt>
                <dd className="text-gray-900 font-medium">
                  {processingTimeMs} ms
                </dd>
              </>
            )}
            {modelInfo?.classifier && (
              <>
                <dt className="text-gray-500">Classifier</dt>
                <dd className="text-gray-900">
                  {modelInfo.classifier.name} v{modelInfo.classifier.version}
                </dd>
              </>
            )}
            {modelInfo?.detector && (
              <>
                <dt className="text-gray-500">Detector</dt>
                <dd className="text-gray-900">
                  {modelInfo.detector.name} v{modelInfo.detector.version}
                </dd>
              </>
            )}
            {modelInfo?.calibration_enabled !== undefined && (
              <>
                <dt className="text-gray-500">Calibration</dt>
                <dd className="text-gray-900">
                  {modelInfo.calibration_enabled ? 'Enabled' : 'Disabled'}
                </dd>
              </>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
