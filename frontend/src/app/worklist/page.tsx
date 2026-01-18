'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { format } from 'date-fns';
import apiClient, { StudySummary, WorklistResponse } from '@/lib/api';
import clsx from 'clsx';
import {
  FunnelIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

const triageColors = {
  URGENT: 'bg-red-100 text-red-800',
  ROUTINE: 'bg-yellow-100 text-yellow-800',
  NORMAL: 'bg-green-100 text-green-800',
};

const statusColors = {
  completed: 'bg-green-100 text-green-800',
  processing: 'bg-blue-100 text-blue-800',
  queued: 'bg-gray-100 text-gray-800',
  failed: 'bg-red-100 text-red-800',
  pending: 'bg-gray-100 text-gray-600',
};

export default function WorklistPage() {
  const [worklist, setWorklist] = useState<WorklistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<string | null>(null);
  const pageSize = 20;

  const fetchWorklist = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getWorklist(page, pageSize, filter || undefined);
      setWorklist(data);
    } catch (error) {
      console.error('Failed to fetch worklist:', error);
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    fetchWorklist();
  }, [fetchWorklist]);

  const totalPages = worklist ? Math.ceil(worklist.total / pageSize) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Worklist</h1>
        <div className="flex items-center space-x-2">
          <FunnelIcon className="w-5 h-5 text-gray-400" />
          <select
            value={filter || ''}
            onChange={(e) => {
              setFilter(e.target.value || null);
              setPage(1);
            }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          >
            <option value="">All Triage Levels</option>
            <option value="URGENT">Urgent</option>
            <option value="ROUTINE">Routine</option>
            <option value="NORMAL">Normal</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Study
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Patient ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  View
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Triage
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Latency
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center">
                    <div className="w-8 h-8 spinner mx-auto" />
                  </td>
                </tr>
              ) : worklist?.studies.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                    No studies found
                  </td>
                </tr>
              ) : (
                worklist?.studies.map((study) => (
                  <tr key={study.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {study.accession_number || study.id.slice(0, 8)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {study.study_date
                          ? format(new Date(study.study_date), 'MMM d, yyyy')
                          : '-'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {study.patient_id || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {study.view_position || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {study.triage_level ? (
                        <span
                          className={clsx(
                            'inline-flex px-2 py-1 text-xs font-semibold rounded-full',
                            triageColors[study.triage_level as keyof typeof triageColors]
                          )}
                        >
                          {study.triage_level}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={clsx(
                          'inline-flex px-2 py-1 text-xs font-medium rounded-full',
                          statusColors[study.status as keyof typeof statusColors] ||
                            'bg-gray-100 text-gray-600'
                        )}
                      >
                        {study.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(study.created_at), 'HH:mm:ss')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {study.processing_time_ms
                        ? `${study.processing_time_ms} ms`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <Link
                        href={`/study/${study.id}`}
                        className="text-primary-600 hover:text-primary-800 inline-flex items-center"
                      >
                        <EyeIcon className="w-4 h-4 mr-1" />
                        View
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {worklist && totalPages > 1 && (
          <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Showing {(page - 1) * pageSize + 1} to{' '}
              {Math.min(page * pageSize, worklist.total)} of {worklist.total} studies
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-md border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                <ChevronLeftIcon className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-600">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 rounded-md border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
