import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Users, BookOpen, Database, Activity } from 'lucide-react';
import { UserManagement } from '../components/Admin/UserManagement';
import { NotebookManagement } from '../components/Admin/NotebookManagement';
import { ConnectionManagement } from '../components/Admin/ConnectionManagement';
import { TokenMetrics } from '../components/Admin/TokenMetrics';

type AdminTab = 'users' | 'notebooks' | 'connections' | 'metrics';

export function Admin() {
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const navigate = useNavigate();

  const tabs = [
    { id: 'users' as const, label: 'Users', icon: Users },
    { id: 'notebooks' as const, label: 'Notebooks', icon: BookOpen },
    { id: 'connections' as const, label: 'DB Connections', icon: Database },
    { id: 'metrics' as const, label: 'Usage Metrics', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/')}
                className="flex items-center text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back
              </button>
              <h1 className="ml-6 text-xl font-semibold text-white">Admin Dashboard</h1>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'notebooks' && <NotebookManagement />}
        {activeTab === 'connections' && <ConnectionManagement />}
        {activeTab === 'metrics' && <TokenMetrics />}
      </div>
    </div>
  );
}
