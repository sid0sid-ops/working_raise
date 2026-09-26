import type React from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import { RaisePage } from '../features/raise';

export const AppRouter: React.FC = () => {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<RaisePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  );
};
