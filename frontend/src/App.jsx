import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import LandingPage from './pages/LandingPage';
import WorkflowLibrary from './pages/WorkflowLibrary';
import CreateWorkflow from './pages/CreateWorkflow';
import DemoPage from './pages/DemoPage';
import ExecutionView from './pages/ExecutionView';
import ReceiptView from './pages/ReceiptView';
import ActivityView from './pages/ActivityView';

export default function App() {
  return (
    <BrowserRouter>
      {/* Global Background Visual */}
      <div className="global-flow-bg" />
      
      <div className="flex flex-col min-h-screen">
        <Header />
        
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-8 py-8 relative z-10">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/demo" element={<DemoPage />} />
            <Route path="/workflows" element={<WorkflowLibrary />} />
            <Route path="/workflows/create" element={<CreateWorkflow />} />
            <Route path="/run/:workflowId" element={<ExecutionView />} />
            <Route path="/receipt/:runId" element={<ReceiptView />} />
            <Route path="/activity" element={<ActivityView />} />
          </Routes>
        </main>
        
        <Footer />
      </div>
    </BrowserRouter>
  );
}
