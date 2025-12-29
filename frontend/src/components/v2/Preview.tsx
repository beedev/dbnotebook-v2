/**
 * Preview Component - NotebookLM-inspired UI Redesign
 *
 * This component demonstrates the new clean, minimal design.
 * Import and render this component to preview the new UI.
 */

import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { ChatHeader, MessageBubble, InputBox, EmptyState } from './Chat';
import type { Notebook, ModelGroup, Document, Message, ModelProvider } from '../../types';

// Mock data for preview
const mockNotebooks: Notebook[] = [
  { id: '1', name: 'Sales Playbook 2024', documentCount: 5, createdAt: new Date(), updatedAt: new Date() },
  { id: '2', name: 'Product Documentation', documentCount: 12, createdAt: new Date(), updatedAt: new Date() },
  { id: '3', name: 'Customer Research', documentCount: 3, createdAt: new Date(), updatedAt: new Date() },
];

const mockModels: ModelGroup[] = [
  {
    provider: 'ollama',
    models: [
      { name: 'llama3.1:latest', displayName: 'Llama 3.1 (4.7 GB)' },
      { name: 'mistral:latest', displayName: 'Mistral (4.1 GB)' },
    ],
  },
  {
    provider: 'openai',
    models: [
      { name: 'gpt-4o', displayName: 'GPT-4o' },
      { name: 'gpt-4o-mini', displayName: 'GPT-4o Mini' },
    ],
  },
];

const mockDocuments: Document[] = [
  { source_id: '1', filename: 'Q4_Strategy.pdf', active: true, chunk_count: 24, file_type: 'pdf' },
  { source_id: '2', filename: 'Competitor_Analysis.docx', active: true, chunk_count: 18, file_type: 'docx' },
  { source_id: '3', filename: 'Market_Research_2024.pptx', active: false, chunk_count: 32, file_type: 'pptx' },
  { source_id: '4', filename: 'customer_feedback.jpg', active: true, chunk_count: 1, file_type: 'jpg' },
];

const mockMessages: Message[] = [
  {
    id: '1',
    role: 'user',
    content: 'What are the key strategies outlined in the Q4 document?',
    timestamp: new Date(Date.now() - 300000),
  },
  {
    id: '2',
    role: 'assistant',
    content: `Based on the Q4 Strategy document, here are the key strategies outlined:

1. **Digital-First Customer Engagement**
   - Expand self-service portals
   - Implement AI-powered chatbots for 24/7 support
   - Launch mobile app v2.0 with enhanced features

2. **Market Expansion**
   - Target 3 new geographic regions
   - Partner with local distributors
   - Localize content for each market

3. **Product Innovation**
   - Release 2 major product updates
   - Beta test AI features with select customers
   - Integrate with popular third-party tools

The document emphasizes a **balanced approach** between growth and customer retention, with specific KPIs for each initiative.`,
    timestamp: new Date(Date.now() - 240000),
    sources: [
      { filename: 'Q4_Strategy.pdf', page: 4, score: 0.94, snippet: 'Digital-first engagement strategy focusing on...' },
      { filename: 'Q4_Strategy.pdf', page: 12, score: 0.87, snippet: 'Market expansion targets for Q4 include...' },
      { filename: 'Competitor_Analysis.docx', page: 8, score: 0.72, snippet: 'Competitor benchmarking shows...' },
    ],
  },
  {
    id: '3',
    role: 'user',
    content: 'How does this compare to what competitors are doing?',
    timestamp: new Date(Date.now() - 180000),
  },
  {
    id: '4',
    role: 'assistant',
    content: `Great question! Here's a comparison with key competitors:

| Strategy Area | Our Approach | Competitor A | Competitor B |
|---------------|--------------|--------------|--------------|
| Digital Channels | Multi-platform | Web-only | Mobile-first |
| AI Integration | Full suite | Limited | None |
| Market Focus | Global expansion | Regional | Enterprise |

**Key Differentiators:**
- We're investing more heavily in AI capabilities
- Our multi-platform approach provides broader coverage
- Competitor A has stronger enterprise relationships

The analysis suggests we should accelerate our AI roadmap to maintain competitive advantage.`,
    timestamp: new Date(Date.now() - 120000),
    sources: [
      { filename: 'Competitor_Analysis.docx', page: 3, score: 0.91 },
      { filename: 'Competitor_Analysis.docx', page: 15, score: 0.84 },
    ],
  },
];

export function Preview() {
  const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(mockNotebooks[0]);
  const [selectedModel, setSelectedModel] = useState('llama3.1:latest');
  const [selectedProvider, setSelectedProvider] = useState<ModelProvider>('ollama');
  const [documents, setDocuments] = useState(mockDocuments);
  const [messages] = useState(mockMessages);

  // Mock handlers
  const handleCreateNotebook = async (name: string) => {
    console.log('Create notebook:', name);
    return null;
  };

  const handleDeleteNotebook = async (id: string) => {
    console.log('Delete notebook:', id);
    return true;
  };

  const handleUpdateNotebook = async (id: string, data: Partial<Notebook>) => {
    console.log('Update notebook:', id, data);
    return true;
  };

  const handleUploadDocument = async (file: File) => {
    console.log('Upload document:', file.name);
    return true;
  };

  const handleDeleteDocument = async (sourceId: string) => {
    setDocuments((prev) => prev.filter((d) => d.source_id !== sourceId));
    return true;
  };

  const handleToggleDocument = async (sourceId: string, active: boolean) => {
    setDocuments((prev) =>
      prev.map((d) => (d.source_id === sourceId ? { ...d, active } : d))
    );
    return true;
  };

  const handleSendMessage = (message: string) => {
    console.log('Send message:', message);
  };

  return (
    <div className="h-screen flex bg-[var(--color-bg-primary)]">
      {/* Sidebar */}
      <Sidebar
        notebooks={mockNotebooks}
        selectedNotebook={selectedNotebook}
        onSelectNotebook={setSelectedNotebook}
        onCreateNotebook={handleCreateNotebook}
        onDeleteNotebook={handleDeleteNotebook}
        onUpdateNotebook={handleUpdateNotebook}
        models={mockModels}
        selectedModel={selectedModel}
        selectedProvider={selectedProvider}
        onSelectModel={(model, provider) => {
          setSelectedModel(model);
          setSelectedProvider(provider);
        }}
        documents={documents}
        onUploadDocument={handleUploadDocument}
        onDeleteDocument={handleDeleteDocument}
        onToggleDocument={handleToggleDocument}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <ChatHeader
          notebookName={selectedNotebook?.name || null}
          messageCount={messages.length}
        />

        {/* Messages */}
        {messages.length === 0 ? (
          <EmptyState
            hasNotebook={!!selectedNotebook}
            hasSources={documents.some((d) => d.active)}
            notebookName={selectedNotebook?.name}
          />
        ) : (
          <div className="flex-1 overflow-y-auto">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onCopy={(content) => console.log('Copied:', content.slice(0, 50))}
              />
            ))}
          </div>
        )}

        {/* Input */}
        <InputBox
          onSend={handleSendMessage}
          disabled={!selectedNotebook}
          onFileUpload={handleUploadDocument}
        />
      </main>
    </div>
  );
}

export default Preview;
