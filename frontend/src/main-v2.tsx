/**
 * DBNotebook v2 Preview Entry Point
 *
 * This entry point uses the new NotebookLM-inspired design.
 * To preview, temporarily rename this file to main.tsx
 * or update index.html to point to this file.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/index.css';
import { Preview } from './components/v2/Preview';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Preview />
  </StrictMode>
);
