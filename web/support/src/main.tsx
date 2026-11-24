import React from 'react';
import { createRoot } from 'react-dom/client';
import { AdminApp } from '../../src/ui';
import '../../src/style.css';

createRoot(document.getElementById('root')!).render(<AdminApp />);
