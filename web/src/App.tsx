import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AskPage } from './pages/AskPage';
import { DecisionsPage } from './pages/DecisionsPage';
import { HomePage } from './pages/HomePage';
import { HowItWorksPage } from './pages/HowItWorksPage';
import { PeoplePage } from './pages/PeoplePage';
import { RepoOverviewPage } from './pages/RepoOverviewPage';
import { ReposPage } from './pages/ReposPage';
import { RolesPage } from './pages/RolesPage';
import { TrailsPage } from './pages/TrailsPage';
import { WhyCardPage } from './pages/WhyCardPage';

/** Route table for the whole app. */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/how" element={<HowItWorksPage />} />
        <Route path="/roles" element={<RolesPage />} />
        <Route path="/repos" element={<ReposPage />} />
        <Route path="/repo/:repoId" element={<RepoOverviewPage />} />
        <Route path="/repo/:repoId/why" element={<WhyCardPage />} />
        <Route path="/repo/:repoId/trails" element={<TrailsPage />} />
        <Route path="/repo/:repoId/ask" element={<AskPage />} />
        <Route path="/repo/:repoId/decisions" element={<DecisionsPage />} />
        <Route path="/repo/:repoId/people" element={<PeoplePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
