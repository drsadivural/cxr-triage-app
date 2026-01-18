'use client';

import { useEffect, useState } from 'react';
import { BellIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import apiClient from '@/lib/api';

export default function Header() {
  const [health, setHealth] = useState<{ status: string; services: Record<string, string> } | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await apiClient.getHealth();
        setHealth(data);
      } catch (error) {
        setHealth({ status: 'unhealthy', services: {} });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health?.status === 'healthy';

  return (
    <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">
          AI-Powered Chest X-ray Analysis
        </h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* System Status */}
        <div className="flex items-center space-x-2">
          {isHealthy ? (
            <CheckCircleIcon className="w-5 h-5 text-green-500" />
          ) : (
            <ExclamationCircleIcon className="w-5 h-5 text-red-500" />
          )}
          <span className={`text-sm ${isHealthy ? 'text-green-600' : 'text-red-600'}`}>
            {isHealthy ? 'System Online' : 'System Degraded'}
          </span>
        </div>

        {/* Notifications */}
        <button className="p-2 text-gray-400 hover:text-gray-500 rounded-full hover:bg-gray-100">
          <BellIcon className="w-6 h-6" />
        </button>
      </div>
    </header>
  );
}
