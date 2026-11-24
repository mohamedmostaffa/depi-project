import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({
  configFile: false,
  root: process.cwd(),
  plugins: [(await import('@vitejs/plugin-react')).default()],
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true },
  appType: 'custom',
});

try {
  const { CustomerPortal, AdminApp } = await server.ssrLoadModule('/src/ui.tsx');
  globalThis.sessionStorage = { getItem: key => key === 'brandmind_admin_token' ? 'staff-token-present' : null };

  const customer = renderToStaticMarkup(React.createElement(CustomerPortal));
  assert.match(customer, /Conversation history/);
  assert.match(customer, /No conversations yet/);
  assert.doesNotMatch(customer, /Preview|Admin access token|Support dashboard|Choose a conversation/);

  const support = renderToStaticMarkup(React.createElement(AdminApp));
  assert.match(support, /Admin access token/);
  assert.doesNotMatch(support, /Choose a conversation to preview|Admin preview/);

  for (const entry of ['customer', 'support']) {
    const html = await readFile(join('dist', entry, 'index.html'), 'utf8');
    assert.match(html, /<div id="root"><\/div>/);
  }

  const customerAssets = await readdir(join('dist', 'customer', 'assets'));
  const customerBundle = (await Promise.all(customerAssets.filter(file => file.endsWith('.js')).map(file => readFile(join('dist', 'customer', 'assets', file), 'utf8')))).join('\n');
  assert.doesNotMatch(customerBundle, /\/admin\/(?:stats|conversations|analytics)/);
  assert.doesNotMatch(customerBundle, /brandmind_admin_token|Admin access token/);

  const supportAssets = await readdir(join('dist', 'support', 'assets'));
  const supportBundle = (await Promise.all(supportAssets.filter(file => file.endsWith('.js')).map(file => readFile(join('dist', 'support', 'assets', file), 'utf8')))).join('\n');
  assert.match(supportBundle, /\/admin\/stats/);
  console.log('Customer/support portal separation checks passed (7 cases).');
} finally {
  await server.close();
}
