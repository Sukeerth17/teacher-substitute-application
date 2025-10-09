import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App'; 

const rootElement = document.getElementById('root');

if (rootElement) {
  // Use the modern React 18+ way to render the app
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}