import React from 'react';
import { createRoot } from 'react-dom/client';

document.title = 'TEST PAGE';

try {
  const root = createRoot(document.getElementById('root'));
  root.render(React.createElement('div', { style: { padding: '50px', textAlign: 'center' } },
    React.createElement('h1', null, 'TEST RENDER OK'),
    React.createElement('p', null, 'If you can see this, React rendering works.')
  ));
} catch (e) {
  document.getElementById('root').innerHTML = 'ERROR: ' + e.message;
}
