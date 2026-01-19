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
  ExclamationTriangleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

type TabType = 'database' | 'llm' | 'ai';

// Default settings for when API fails
const defaultSettings: Settings = {
  database: {
    db_type: 'postgres',
    host: 'localhost',
    port: 5432,
    user: 'cxr_user',
    password: '',
    dbname: 'cxr_triage',
    ssl_mode: 'prefer',
  },
  llm: {
    active_provider: null,
    llm_rewrite_enabled: false,
    azure_openai: {
      enabled: false,
      endpoint: '',
      deployment_name: '',
      api_version: '2024-02-15-preview',
      api_key: '',
      temperature: 0.3,
      top_p: 0.95,
      max_tokens: 1024,
      streaming: false,
    },
    claude: {
      enabled: false,
      base_url: 'https://api.anthropic.com',
      model: 'claude-3-sonnet-20240229',
      api_key: '',
      temperature: 0.3,
      top_p: 0.95,
      max_tokens: 1024,
    },
    gemini: {
      enabled: false,
      base_url: 'https://generativelanguage.googleapis.com/v1beta',
      model: 'gemini-pro',
      api_key: '',
      temperature: 0.3,
      top_p: 0.95,
      max_output_tokens: 1024,
    },
  },
  ai: {
    pneumothorax: { triage_threshold: 0.25, strong_threshold: 0.65, enabled: true },
    pleural_effusion: { triage_threshold: 0.3, strong_threshold: 0.7, enabled: true },
    consolidation: { triage_threshold: 0.35, strong_threshold: 0.7, enabled: true },
    cardiomegaly: { triage_threshold: 0.4, strong_threshold: 0.75, enabled: true },
    edema: { triage_threshold: 0.35, strong_threshold: 0.7, enabled: true },
    nodule: { triage_threshold: 0.3, strong_threshold: 0.65, enabled: true },
    mass: { triage_threshold: 0.25, strong_threshold: 0.6, enabled: true },
    detector_confidence: 0.25,
    detector_iou: 0.45,
    detector_max_boxes: 10,
    calibration_enabled: true,
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('database');
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'success' | 'error' | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchSettings = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await apiClient.getSettings();
      setSettings(data);
    } catch (error: any) {
      console.error('Failed to fetch settings:', error);
      const errorMsg = error.message || 'Failed to load settings from server';
      setLoadError(errorMsg);
      // Use default settings so user can still configure
      setSettings(defaultSettings);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async () => {
    if (!settings) return;

    setSaving(true);
    try {
      const updated = await apiClient.updateSettings(settings);
      setSettings(updated);
      setLoadError(null);
      toast.success('Settings saved successfully');
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      toast.error(error.message || 'Failed to save settings');
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
    } catch (error: any) {
      setConnectionStatus('error');
      toast.error(error.message || 'Connection test failed');
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
        [provider]: { ...(settings.llm as any)[provider], [field]: value },
      },
    });
  };

  const updateLLMRoot = (field: string, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      llm: { ...settings.llm, [field]: value },
    });
  };

  const updateAI = (field: string, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      ai: { ...settings.ai, [field]: value },
    });
  };

  const updateFindingThreshold = (finding: string, field: string, value: number | boolean) => {
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
        <div className="text-center">
          <div className="w-12 h-12 spinner mx-auto mb-4" />
          <p className="text-gray-500">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-gray-700 font-medium">Failed to load settings</p>
        <p className="text-gray-500 text-sm mt-2">{loadError || 'Unknown error'}</p>
        <button
          onClick={fetchSettings}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 inline-flex items-center"
        >
          <ArrowPathIcon className="w-4 h-4 mr-2" />
          Retry
        </button>
      </div>
    );
  }

  const tabs = [
    { id: 'database', name: 'Database', icon: CircleStackIcon },
    { id: 'llm', name: 'LLM Providers', icon: ChatBubbleLeftRightIcon },
    { id: 'ai', name: 'AI Settings', icon: CpuChipIcon },
  ];

  const findings = [
    { key: 'pneumothorax', label: 'Pneumothorax' },
    { key: 'pleural_effusion', label: 'Pleural Effusion' },
    { key: 'consolidation', label: 'Consolidation' },
    { key: 'cardiomegaly', label: 'Cardiomegaly' },
    { key: 'edema', label: 'Edema' },
    { key: 'nodule', label: 'Nodule' },
    { key: 'mass', label: 'Mass' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <div className="flex items-center space-x-2">
          {loadError && (
            <span className="text-sm text-yellow-600 flex items-center mr-4">
              <ExclamationTriangleIcon className="w-4 h-4 mr-1" />
              Using defaults
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {loadError && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div className="flex items-start">
            <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500 mt-0.5 mr-3" />
            <div>
              <p className="text-sm text-yellow-800 font-medium">Could not load saved settings</p>
              <p className="text-sm text-yellow-700 mt-1">{loadError}</p>
              <p className="text-sm text-yellow-600 mt-2">
                Default settings are shown. Configure and save to persist your settings.
              </p>
            </div>
          </div>
        </div>
      )}

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
                  onChange={(e) => updateDatabase('port', parseInt(e.target.value) || 5432)}
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
                  placeholder={settings.database.password === '********' ? '(unchanged)' : ''}
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
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Enable LLM Report Rewriting
                  </label>
                  <p className="text-sm text-gray-500">
                    Use AI to enhance and rewrite generated reports
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.llm.llm_rewrite_enabled}
                    onChange={(e) => updateLLMRoot('llm_rewrite_enabled', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Active Provider
                </label>
                <select
                  value={settings.llm.active_provider || ''}
                  onChange={(e) => updateLLMRoot('active_provider', e.target.value || null)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  disabled={!settings.llm.llm_rewrite_enabled}
                >
                  <option value="">None</option>
                  <option value="azure_openai">Azure OpenAI</option>
                  <option value="claude">Claude (Anthropic)</option>
                  <option value="gemini">Google Gemini</option>
                </select>
              </div>
            </div>
          </div>

          {/* Azure OpenAI */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Azure OpenAI</h3>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.llm.azure_openai.enabled}
                  onChange={(e) => updateLLM('azure_openai', 'enabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
            <div className="card-body space-y-4">
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
                    Temperature ({settings.llm.azure_openai.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.llm.azure_openai.temperature}
                    onChange={(e) => updateLLM('azure_openai', 'temperature', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={settings.llm.azure_openai.max_tokens}
                    onChange={(e) => updateLLM('azure_openai', 'max_tokens', parseInt(e.target.value) || 1024)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Claude */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Claude (Anthropic)</h3>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.llm.claude.enabled}
                  onChange={(e) => updateLLM('claude', 'enabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
            <div className="card-body space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model
                  </label>
                  <select
                    value={settings.llm.claude.model}
                    onChange={(e) => updateLLM('claude', 'model', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                    <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                    <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                  </select>
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Temperature ({settings.llm.claude.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.llm.claude.temperature}
                    onChange={(e) => updateLLM('claude', 'temperature', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={settings.llm.claude.max_tokens}
                    onChange={(e) => updateLLM('claude', 'max_tokens', parseInt(e.target.value) || 1024)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Gemini */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Google Gemini</h3>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.llm.gemini.enabled}
                  onChange={(e) => updateLLM('gemini', 'enabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
            <div className="card-body space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model
                  </label>
                  <select
                    value={settings.llm.gemini.model}
                    onChange={(e) => updateLLM('gemini', 'model', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="gemini-pro">Gemini Pro</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </select>
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Temperature ({settings.llm.gemini.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.llm.gemini.temperature}
                    onChange={(e) => updateLLM('gemini', 'temperature', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Output Tokens
                  </label>
                  <input
                    type="number"
                    value={settings.llm.gemini.max_output_tokens}
                    onChange={(e) => updateLLM('gemini', 'max_output_tokens', parseInt(e.target.value) || 1024)}
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
            <div className="card-body space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confidence Threshold ({settings.ai.detector_confidence})
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="0.9"
                    step="0.05"
                    value={settings.ai.detector_confidence}
                    onChange={(e) => updateAI('detector_confidence', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    IoU Threshold ({settings.ai.detector_iou})
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="0.9"
                    step="0.05"
                    value={settings.ai.detector_iou}
                    onChange={(e) => updateAI('detector_iou', parseFloat(e.target.value))}
                    className="w-full"
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
                    onChange={(e) => updateAI('detector_max_boxes', parseInt(e.target.value) || 10)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Probability Calibration
                  </label>
                  <p className="text-sm text-gray-500">
                    Apply calibration to model probabilities
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.ai.calibration_enabled}
                    onChange={(e) => updateAI('calibration_enabled', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Finding Thresholds */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-gray-900">Finding Thresholds</h3>
              <p className="text-sm text-gray-500 mt-1">
                Configure triage and strong positive thresholds for each finding
              </p>
            </div>
            <div className="card-body">
              <div className="space-y-6">
                {findings.map((finding) => (
                  <div key={finding.key} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">{finding.label}</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={(settings.ai as any)[finding.key]?.enabled ?? true}
                          onChange={(e) => updateFindingThreshold(finding.key, 'enabled', e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Triage Threshold ({((settings.ai as any)[finding.key]?.triage_threshold ?? 0.3).toFixed(2)})
                        </label>
                        <input
                          type="range"
                          min="0.1"
                          max="0.9"
                          step="0.05"
                          value={(settings.ai as any)[finding.key]?.triage_threshold ?? 0.3}
                          onChange={(e) => updateFindingThreshold(finding.key, 'triage_threshold', parseFloat(e.target.value))}
                          className="w-full"
                          disabled={!((settings.ai as any)[finding.key]?.enabled ?? true)}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Strong Threshold ({((settings.ai as any)[finding.key]?.strong_threshold ?? 0.7).toFixed(2)})
                        </label>
                        <input
                          type="range"
                          min="0.1"
                          max="0.9"
                          step="0.05"
                          value={(settings.ai as any)[finding.key]?.strong_threshold ?? 0.7}
                          onChange={(e) => updateFindingThreshold(finding.key, 'strong_threshold', parseFloat(e.target.value))}
                          className="w-full"
                          disabled={!((settings.ai as any)[finding.key]?.enabled ?? true)}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
