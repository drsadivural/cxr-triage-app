'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient, { DashboardMetrics, ModelsResponse } from '@/lib/api';
import {
  DocumentMagnifyingGlassIcon,
  QueueListIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend);

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [metricsData, modelsData] = await Promise.all([
          apiClient.getDashboardMetrics(),
          apiClient.getModels(),
        ]);
        setMetrics(metricsData);
        setModels(modelsData);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const triageChartData = metrics
    ? {
        labels: ['Normal', 'Routine', 'Urgent'],
        datasets: [
          {
            data: [
              metrics.triage_distribution.normal,
              metrics.triage_distribution.routine,
              metrics.triage_distribution.urgent,
            ],
            backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'],
            borderWidth: 0,
          },
        ],
      }
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Disclaimer Banner */}
      <div className="disclaimer-banner rounded-lg">
        <div className="flex items-start">
          <ExclamationTriangleIcon className="w-5 h-5 text-amber-500 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-medium text-amber-800">
              AI Assistance Only - Not for Standalone Diagnosis
            </h3>
            <p className="mt-1 text-sm text-amber-700">
              This system provides AI-assisted analysis to support clinical decision-making.
              All findings must be reviewed and confirmed by a qualified radiologist.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/analyze"
          className="card p-6 hover:shadow-md transition-shadow flex items-center"
        >
          <div className="p-3 bg-primary-100 rounded-lg mr-4">
            <DocumentMagnifyingGlassIcon className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Analyze New Image</h3>
            <p className="text-sm text-gray-500">
              Upload a chest X-ray for AI analysis
            </p>
          </div>
        </Link>

        <Link
          href="/worklist"
          className="card p-6 hover:shadow-md transition-shadow flex items-center"
        >
          <div className="p-3 bg-green-100 rounded-lg mr-4">
            <QueueListIcon className="w-8 h-8 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">View Worklist</h3>
            <p className="text-sm text-gray-500">
              Review recent studies and results
            </p>
          </div>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Studies Today</p>
              <p className="text-2xl font-bold text-gray-900">
                {metrics?.studies_today || 0}
              </p>
            </div>
            <div className="p-2 bg-blue-100 rounded-lg">
              <ChartBarIcon className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">This Week</p>
              <p className="text-2xl font-bold text-gray-900">
                {metrics?.studies_this_week || 0}
              </p>
            </div>
            <div className="p-2 bg-purple-100 rounded-lg">
              <ChartBarIcon className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Avg. Latency</p>
              <p className="text-2xl font-bold text-gray-900">
                {metrics?.latency.avg_processing_time_ms.toFixed(0) || 0} ms
              </p>
            </div>
            <div className="p-2 bg-green-100 rounded-lg">
              <ClockIcon className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">P95 Latency</p>
              <p className="text-2xl font-bold text-gray-900">
                {metrics?.latency.p95_processing_time_ms.toFixed(0) || 0} ms
              </p>
            </div>
            <div className="p-2 bg-yellow-100 rounded-lg">
              <ClockIcon className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts and Model Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Triage Distribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900">Triage Distribution</h3>
          </div>
          <div className="card-body">
            {triageChartData && metrics?.triage_distribution.total > 0 ? (
              <div className="h-64 flex items-center justify-center">
                <Doughnut
                  data={triageChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'bottom',
                      },
                    },
                  }}
                />
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No data available
              </div>
            )}
          </div>
        </div>

        {/* Model Status */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900">Model Status</h3>
          </div>
          <div className="card-body space-y-4">
            {/* Classifier */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">Classifier</h4>
                {models?.classifier?.status === 'loaded' ? (
                  <span className="flex items-center text-green-600 text-sm">
                    <CheckCircleIcon className="w-4 h-4 mr-1" />
                    Loaded
                  </span>
                ) : (
                  <span className="flex items-center text-red-600 text-sm">
                    <ExclamationTriangleIcon className="w-4 h-4 mr-1" />
                    Not Loaded
                  </span>
                )}
              </div>
              {models?.classifier && (
                <div className="text-sm text-gray-600">
                  <p>{models.classifier.name}</p>
                  <p className="text-xs text-gray-400">
                    v{models.classifier.version}
                  </p>
                </div>
              )}
            </div>

            {/* Detector */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">Detector</h4>
                {models?.detector?.status === 'loaded' ? (
                  <span className="flex items-center text-green-600 text-sm">
                    <CheckCircleIcon className="w-4 h-4 mr-1" />
                    Loaded
                  </span>
                ) : (
                  <span className="flex items-center text-red-600 text-sm">
                    <ExclamationTriangleIcon className="w-4 h-4 mr-1" />
                    Not Loaded
                  </span>
                )}
              </div>
              {models?.detector && (
                <div className="text-sm text-gray-600">
                  <p>{models.detector.name}</p>
                  <p className="text-xs text-gray-400">
                    v{models.detector.version}
                  </p>
                </div>
              )}
            </div>

            {!models?.models_available && (
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <p className="text-sm text-amber-800">
                  <strong>Models not available.</strong> Please run the model
                  download script or check the Settings page.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
