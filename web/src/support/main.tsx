import React from 'react';
import { createRoot } from 'react-dom/client';
import { AdminApp } from '../ui';
import '../style.css';

createRoot(document.getElementById('root')!).render(<AdminApp />);
