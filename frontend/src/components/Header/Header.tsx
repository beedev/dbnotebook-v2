/**
 * Global Header Component
 *
 * Features:
 * - Navigation tabs for all features (RAG Chat, Analytics, Chat with Data)
 * - Global model selector that applies to all features
 * - Deep space terminal theme styling
 */

import { MessageSquare, BarChart3, Database, Cpu, Sparkles, Bot, Cloud, Zap, Terminal } from 'lucide-react';
import { useApp, type AppView } from '../../contexts/AppContext';
import type { ModelProvider } from '../../types';

const providerIcons: Record<ModelProvider, React.ReactNode> = {
  ollama: <Cpu className="w-4 h-4" />,
  openai: <Sparkles className="w-4 h-4" />,
  anthropic: <Bot className="w-4 h-4" />,
  google: <Cloud className="w-4 h-4" />,
};

const providerColors: Record<ModelProvider, string> = {
  ollama: 'text-glow',
  openai: 'text-green-400',
  anthropic: 'text-orange-400',
  google: 'text-blue-400',
};

const providerLabels: Record<ModelProvider, string> = {
  ollama: 'Ollama (Local)',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
};

interface NavTab {
  id: AppView;
  label: string;
  icon: React.ReactNode;
  color: string;
  hoverColor: string;
}

const navTabs: NavTab[] = [
  {
    id: 'chat',
    label: 'RAG Chat',
    icon: <MessageSquare className="w-4 h-4" />,
    color: 'text-glow',
    hoverColor: 'hover:bg-glow/10',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: <BarChart3 className="w-4 h-4" />,
    color: 'text-nebula-bright',
    hoverColor: 'hover:bg-nebula/10',
  },
  {
    id: 'sql-chat',
    label: 'Chat with Data',
    icon: <Database className="w-4 h-4" />,
    color: 'text-cyan-400',
    hoverColor: 'hover:bg-cyan-500/10',
  },
  {
    id: 'query-api',
    label: 'Query API',
    icon: <Terminal className="w-4 h-4" />,
    color: 'text-amber-400',
    hoverColor: 'hover:bg-amber-500/10',
  },
];

export function Header() {
  const {
    currentView,
    setCurrentView,
    models,
    selectedModel,
    selectedProvider,
    isLoadingModels,
    selectModel,
  } = useApp();

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const [provider, model] = e.target.value.split('::');
    selectModel(model, provider as ModelProvider);
  };

  const currentModelValue = `${selectedProvider}::${selectedModel}`;

  return (
    <header className="h-14 flex items-center justify-between px-4 bg-void-light border-b border-void-surface shrink-0">
      {/* Logo and Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-glow/20 flex items-center justify-center">
            <Zap className="w-5 h-5 text-glow" />
          </div>
          <h1 className="text-lg font-bold text-text font-[family-name:var(--font-display)]">
            <span className="gradient-text">DB</span>Notebook
          </h1>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1">
        {navTabs.map((tab) => {
          const isActive = currentView === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setCurrentView(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg
                font-medium text-sm transition-all duration-200
                ${isActive
                  ? `${tab.color} bg-void-surface`
                  : `text-text-muted ${tab.hoverColor} hover:text-text`
                }
              `}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Model Selector */}
      <div className="flex items-center gap-2">
        <div className="relative">
          <select
            value={currentModelValue}
            onChange={handleModelChange}
            disabled={isLoadingModels}
            className={`
              appearance-none
              pl-3 pr-9 py-1.5
              bg-void-surface text-text rounded-lg
              border border-void-lighter
              font-[family-name:var(--font-body)] text-sm
              transition-all duration-200
              hover:border-text-dim
              focus:outline-none focus:border-glow focus:ring-1 focus:ring-glow/30
              disabled:opacity-50 disabled:cursor-not-allowed
              max-w-[200px]
            `}
          >
            {models.map((group) => (
              <optgroup
                key={group.provider}
                label={providerLabels[group.provider] || group.provider}
                className="bg-void-light text-text"
              >
                {group.models.map((model) => (
                  <option
                    key={`${group.provider}::${model.name}`}
                    value={`${group.provider}::${model.name}`}
                    className="bg-void-light text-text"
                  >
                    {model.displayName || model.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>

          {/* Provider icon */}
          <div className="absolute inset-y-0 right-0 flex items-center pr-2.5 pointer-events-none">
            <span className={providerColors[selectedProvider]}>
              {providerIcons[selectedProvider]}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
