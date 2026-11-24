import React from 'react';
import { createRoot } from 'react-dom/client';
import { CustomerPortal } from '../../src/ui';
import '../../src/style.css';

createRoot(document.getElementById('root')!).render(<CustomerPortal />);
