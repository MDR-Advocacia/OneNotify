import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import ReviewForm from './ReviewForm';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {window.location.pathname === '/revisao' ? <ReviewForm /> : <App />}
  </React.StrictMode>
);
