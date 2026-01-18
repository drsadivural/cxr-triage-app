'use client';

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import apiClient, { Settings } from '@/lib/api';
import clsx from 'clsx';
import {
  CircleStackIcon,
  CpuChipIcon,
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

type TabType = 'database' | 'llm' | 'ai';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('database');
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'success' | 'error' | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await apiClient.getSettings();
        setSettings(data);
      } catch (error) {
        console.error('Failed to fetch settings:', error);
        toast.error('Failed to load settings');
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleSave = async () => {
    if (!settings) return;

    setSaving(true);
    try {
      const updated = await apiClient.updateSettings(settings);
      setSettings(updated);
      toast.success('Settings saved successfully');
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    if (!settings) return;

    setTestingConnection(true);
    setConnectionStatus(null);
    try {
      const result = await apiClient.testConnection(settings.database);
      setConnectionStatus(result.success ? 'success' : 'error');
      if (result.success) {
        toast.success('Connection successful');
      } else {
        toast.error(result.message || 'Connection failed');
      }
    } catch (error) {
      setConnectionStatus('error');
      toast.error('Connection test failed');
    } finally {
      setTestingConnection(false);
    }
  };

  const updateDatabase = (field: string, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      database: { ...settings.database, [field]: value },
    });
  };

  const updateLLM = (provider: string, field: string, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      llm: {
        ...settings.llm,
        [provider]: { ...settings.llm[provider as keyof typeof settings.llm], [field]: value },
      },
    });
  };

  const updateAI = (field: string, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      ai: { ...settings.ai, [field]: value },
    });
  };

  const updateFindingThreshold = (finding: string, field: string, value: number) => {
    if (!settings) return;
    setSettings({
      ...settings,
      ai: {
        ...settings.ai,
        [finding]: {
          ...(settings.ai as any)[finding],
          [field]: value,
        },
      },
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 spinner" />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Failed to load settings</p>
      </div>
    );
  }

  const tabs = [
    { id: 'database', name: 'Database', icon: CircleStackIcon },
    { id: 'llm', name: 'LLM Providers', icon: ChatBubbleLeftRightIcon },
    { id: 'ai', name: 'AI Settings', icon: CpuChipIcon },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={clsx(
                'flex items-center py-4 px-1 border-b-2 font-medium text-sm',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              <tab.icon className="w-5 h-5 mr-2" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Database Settings */}
      {activeTab === 'database' && (
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900">Database Configuration</h3>
          </div>
          <div className="card-body space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Database Type
                </label>
                <select
                  value={settings.database.db_type}
                  onChange={(e) => updateDatabase('db_type', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="postgres">PostgreSQL</option>
                  <option value="sqlite">SQLite (Dev Only)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Host
                </label>
                <input
                  type="text"
                  value={settings.database.host}
                  onChange={(e) => updateDatabase('host', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Port
                </label>
                <input
                  type="number"
                  value={settings.database.port}
                  onChange={(e) => updateDatabase('port', parseInt(e.target.value))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Database Name
                </label>
                <input
                  type="text"
                  value={settings.database.dbname}
                  onChange={(e) => updateDatabase('dbname', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username
                </label>
                <input
                  type="text"
                  value={settings.database.user}
                  onChange={(e) => updateDatabase('user', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={settings.database.password}
                  onChange={(e) => updateDatabase('password', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SSL Mode
                </label>
                <select
                  value={settings.database.ssl_mode}
                  onChange={(e) => updateDatabase('ssl_mode', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="disable">Disable</option>
                  <option value="prefer">Prefer</option>
                  <option value="require">Require</option>
                </select>
              </div>
            </div>

            <div className="flex items-center space-x-4 pt-4 border-t">
              <button
                onClick={handleTestConnection}
                disabled={testingConnection}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                {testingConnection ? 'Testing...' : 'Test Connection'}
              </button>
              {connectionStatus === 'success' && (
                <span className="flex items-center text-green-600">
                  <CheckCircleIcon className="w-5 h-5 mr-1" />
                  Connected
                </span>
              )}
              {connectionStatus === 'error' && (
                <span className="flex items-center text-red-600">
                  <XCircleIcon className="w-5 h-5 mr-1" />
                  Failed
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* LLM Settings */}
      {activeTab === 'llm' && (
        <div className="space-y-6">
          {/* Active Provider */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">LLM Configuration</h3>
            </div>
            <div className="card-body space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Active Provider
                </label>
                <select
                  value={settings.llm.active_provider || ''}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      llm: { ...settings.llm, active_provider: e.target.value || null },
                    })
                  }
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="">None (Template Only)</option>
                  <option value="azure_openai">Azure OpenAI</option>
                  <option value="claude">Claude</option>
                  <option value="gemini">Gemini</option>
                </select>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="llm_rewrite"
                  checked={settings.llm.llm_rewrite_enabled}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      llm: { ...settings.llm, llm_rewrite_enabled: e.target.checked },
                    })
                  }
                  className="h-4 w-4 text-primary-600 rounded"
                />
                <label htmlFor="llm_rewrite" className="ml-2 text-sm text-gray-700">
                  Enable LLM Report Rewriting
                </label>
              </div>
            </div>
          </div>

          {/* Azure OpenAI */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">Azure OpenAI</h3>
            </div>
            <div className="card-body space-y-4">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.llm.azure_openai.enabled}
                  onChange={(e) => updateLLM('azure_openai', 'enabled', e.target.checked)}
                  className="h-4 w-4 text-primary-600 rounded"
                />
                <label className="ml-2 text-sm text-gray-700">Enabled</label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Endpoint
                  </label>
                  <input
                    type="text"
                    value={settings.llm.azure_openai.endpoint}
                    onChange={(e) => updateLLM('azure_openai', 'endpoint', e.target.value)}
                    placeholder="https://your-resource.openai.azure.com"
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Deployment Name
                  </label>
                  <input
                    type="text"
                    value={settings.llm.azure_openai.deployment_name}
                    onChange={(e) => updateLLM('azure_openai', 'deployment_name', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Version
                  </label>
                  <input
                    type="text"
                    value={settings.llm.azure_openai.api_version}
                    onChange={(e) => updateLLM('azure_openai', 'api_version', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={settings.llm.azure_openai.api_key}
                    onChange={(e) => updateLLM('azure_openai', 'api_key', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Temperature
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={settings.llm.azure_openai.temperature}
                    onChange={(e) => updateLLM('azure_openai', 'temperature', parseFloat(e.target.value))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={settings.llm.azure_openai.max_tokens}
                    onChange={(e) => updateLLM('azure_openai', 'max_tokens', parseInt(e.target.value))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Claude */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">Claude (Anthropic)</h3>
            </div>
            <div className="card-body space-y-4">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.llm.claude.enabled}
                  onChange={(e) => updateLLM('claude', 'enabled', e.target.checked)}
                  className="h-4 w-4 text-primary-600 rounded"
                />
                <label className="ml-2 text-sm text-gray-700">Enabled</label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model
                  </label>
                  <input
                    type="text"
                    value={settings.llm.claude.model}
                    onChange={(e) => updateLLM('claude', 'model', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={settings.llm.claude.api_key}
                    onChange={(e) => updateLLM('claude', 'api_key', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Gemini */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">Google Gemini</h3>
            </div>
            <div className="card-body space-y-4">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.llm.gemini.enabled}
                  onChange={(e) => updateLLM('gemini', 'enabled', e.target.checked)}
                  className="h-4 w-4 text-primary-600 rounded"
                />
                <label className="ml-2 text-sm text-gray-700">Enabled</label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model
                  </label>
                  <input
                    type="text"
                    value={settings.llm.gemini.model}
                    onChange={(e) => updateLLM('gemini', 'model', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={settings.llm.gemini.api_key}
                    onChange={(e) => updateLLM('gemini', 'api_key', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Settings */}
      {activeTab === 'ai' && (
        <div className="space-y-6">
          {/* Detector Settings */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">Detector Settings</h3>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confidence Threshold
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={settings.ai.detector_confidence}
                    onChange={(e) => updateAI('detector_confidence', parseFloat(e.target.value))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    IoU Threshold
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={settings.ai.detector_iou}
                    onChange={(e) => updateAI('detector_iou', parseFloat(e.target.value))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Boxes
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={settings.ai.detector_max_boxes}
                    onChange={(e) => updateAI('detector_max_boxes', parseInt(e.target.value))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
              <div className="mt-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.ai.calibration_enabled}
                    onChange={(e) => updateAI('calibration_enabled', e.target.checked)}
                    className="h-4 w-4 text-primary-600 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    Enable Probability Calibration
                  </span>
                </label>
              </div>
            </div>
          </div>

          {/* Per-Finding Thresholds */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">Finding Thresholds</h3>
            </div>
            <div className="card-body">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Finding
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Triage Threshold
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Strong Threshold
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Enabled
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {['pneumothorax', 'pleural_effusion', 'consolidation', 'cardiomegaly', 'edema', 'nodule', 'mass'].map(
                      (finding) => (
                        <tr key={finding}>
                          <td className="px-4 py-2 capitalize">
                            {finding.replace('_', ' ')}
                          </td>
                          <td className="px-4 py-2">
                            <input
                              type="number"
                              step="0.05"
                              min="0"
                              max="1"
                              value={(settings.ai as any)[finding]?.triage_threshold || 0.3}
                              onChange={(e) =>
                                updateFindingThreshold(finding, 'triage_threshold', parseFloat(e.target.value))
                              }
                              className="w-20 border border-gray-300 rounded px-2 py-1 text-sm"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input
                              type="number"
                              step="0.05"
                              min="0"
                              max="1"
                              value={(settings.ai as any)[finding]?.strong_threshold || 0.7}
                              onChange={(e) =>
                                updateFindingThreshold(finding, 'strong_threshold', parseFloat(e.target.value))
                              }
                              className="w-20 border border-gray-300 rounded px-2 py-1 text-sm"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input
                              type="checkbox"
                              checked={(settings.ai as any)[finding]?.enabled !== false}
                              onChange={(e) =>
                                updateFindingThreshold(finding, 'enabled', e.target.checked ? 1 : 0)
                              }
                              className="h-4 w-4 text-primary-600 rounded"
                            />
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
