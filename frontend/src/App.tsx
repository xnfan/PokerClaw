import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import AgentManagePage from './pages/AgentManagePage';
import GameSetupPage from './pages/GameSetupPage';
import GamePlayPage from './pages/GamePlayPage';
import ReplayPage from './pages/ReplayPage';
import MonitoringPage from './pages/MonitoringPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="sidebar">
          <h1 className="logo">PokerClaw</h1>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/agents">Agent Management</NavLink>
          <NavLink to="/games/new">New Game</NavLink>
          <NavLink to="/monitoring">Monitoring</NavLink>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/agents" element={<AgentManagePage />} />
            <Route path="/games/new" element={<GameSetupPage />} />
            <Route path="/games/:sessionId" element={<GamePlayPage />} />
            <Route path="/replay/:handId" element={<ReplayPage />} />
            <Route path="/monitoring" element={<MonitoringPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
