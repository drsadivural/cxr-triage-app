'use client';

import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import apiClient, { AuditLog, DashboardMetrics } from '@/lib/api';
import clsx from 'clsx';
import {
  ChartBarIcon,
  ClockIcon,
  DocumentTextIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function AdminPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState<string>('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [metricsData, auditData] = await Promise.all([
          apiClient.getDashboardMetrics(),
          apiClient.getAuditLogs(1, 50, actionFilter || undefined),
        ]);
        setMetrics(metricsData);
        setAuditLogs(auditData.logs);
      } catch (error) {
        console.error('Failed to fetch admin data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [actionFilter]);

  const latencyChartData = metrics
    ? {
        labels: ['Avg', 'P50', 'P95', 'P99'],
        datasets: [
          {
            label: 'Latency (ms)',
            data: [
              metrics.latency.avg_processing_time_ms,
              metrics.latency.p50_processing_time_ms,
              metrics.latency.p95_processing_time_ms,
              metrics.latency.p99_processing_time_ms,
            ],
            backgroundColor: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444'],
          },
        ],
      }
    : null;

  const actionColors: Record<string, string> = {
    study_upload: 'bg-blue-100 text-blue-800',
    analysis_start: 'bg-yellow-100 text-yellow-800',
    analysis_complete: 'bg-green-100 text-green-800',
    analysis_error: 'bg-red-100 text-red-800',
    settings_change: 'bg-purple-100 text-purple-800',
    export: 'bg-gray-100 text-gray-800',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Admin / QA Dashboard</h1>

      {/* Latency Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Latency Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900">Processing Latency (24h)</h3>
          </div>
          <div className="card-body">
            {latencyChartData ? (
              <div className="h-64">
                <Bar
                  data={latencyChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false,
                      },
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        title: {
                          display: true,
                          text: 'Milliseconds',
                        },
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

        {/* Stats Cards */}
        <div className="space-y-4">
          <div className="card p-4">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg mr-4">
                <ChartBarIcon className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Studies (24h)</p>
                <p className="text-2xl font-bold text-gray-900">
                  {metrics?.latency.total_studies || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg mr-4">
                <ClockIcon className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Average Latency</p>
                <p className="text-2xl font-bold text-gray-900">
                  {metrics?.latency.avg_processing_time_ms.toFixed(0) || 0} ms
                </p>
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center">
              <div className="p-3 bg-yellow-100 rounded-lg mr-4">
                <ClockIcon className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">P95 Latency</p>
                <p className="text-2xl font-bold text-gray-900">
                  {metrics?.latency.p95_processing_time_ms.toFixed(0) || 0} ms
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Model Registry */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold text-gray-900">Model Registry</h3>
        </div>
        <div className="card-body">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Model
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Type
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Version
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="px-4 py-3">DenseNet121-All (TorchXRayVision)</td>
                  <td className="px-4 py-3">Classifier</td>
                  <td className="px-4 py-3">1.0.0</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                      Active
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3">Faster R-CNN Detector</td>
                  <td className="px-4 py-3">Detector</td>
                  <td className="px-4 py-3">1.0.0</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                      Active
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Audit Logs */}
      <div className="card">
        <div className="card-header flex justify-between items-center">
          <h3 className="font-semibold text-gray-900">Audit Logs</h3>
          <div className="flex items-center space-x-2">
            <FunnelIcon className="w-4 h-4 text-gray-400" />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-2 py-1 text-sm"
            >
              <option value="">All Actions</option>
              <option value="study_upload">Upload</option>
              <option value="analysis_complete">Analysis Complete</option>
              <option value="analysis_error">Analysis Error</option>
              <option value="settings_change">Settings Change</option>
              <option value="export">Export</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Time
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Action
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Study ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Details
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  IP
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No audit logs found
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(log.created_at), 'MMM d, HH:mm:ss')}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={clsx(
                          'px-2 py-1 text-xs rounded-full',
                          actionColors[log.action] || 'bg-gray-100 text-gray-800'
                        )}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {log.study_id ? log.study_id.slice(0, 8) + '...' : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                      {log.details ? JSON.stringify(log.details) : '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {log.ip_address || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
