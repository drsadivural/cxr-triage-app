'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import {
  HomeIcon,
  DocumentMagnifyingGlassIcon,
  QueueListIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Analyze', href: '/analyze', icon: DocumentMagnifyingGlassIcon },
  { name: 'Worklist', href: '/worklist', icon: QueueListIcon },
  { name: 'Admin / QA', href: '/admin', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col w-64 bg-gray-900">
      {/* Logo */}
      <div className="flex items-center h-16 px-4 bg-gray-800">
        <div className="flex items-center">
          <svg
            className="w-8 h-8 text-primary-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
          <span className="ml-2 text-xl font-bold text-white">CXR Triage</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                'flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              )}
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Disclaimer */}
      <div className="p-4 border-t border-gray-700">
        <div className="p-3 bg-amber-900/50 rounded-lg">
          <p className="text-xs text-amber-200">
            <strong>⚠️ AI Assistance Only</strong>
            <br />
            Not for standalone diagnosis. All findings require radiologist review.
          </p>
        </div>
      </div>

      {/* Version */}
      <div className="px-4 py-2 text-xs text-gray-500">
        Version 1.0.0
      </div>
    </div>
  );
}
