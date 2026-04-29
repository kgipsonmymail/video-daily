import { useState } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import TasksPage from "./pages/TasksPage";
import QueryPage from "./pages/QueryPage";
import DailyPage from "./pages/DailyPage";
import QueuePage from "./pages/QueuePage";
import MatrixPage from "./pages/MatrixPage";
import MusicPage from "./pages/MusicPage";
import VoicePage from "./pages/VoicePage";
import type { Page, Modality } from "./types";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30 * 1000, retry: 1 },
  },
});

function usePageModality() {
  const location = useLocation();

  const page = (location.pathname.replace("/", "") || "tasks") as Page;
  const params = new URLSearchParams(location.search);
  const mod = (params.get("mod") as Modality) || "all";

  return { page, mod };
}

function AppContent() {
  const { page, mod: initMod } = usePageModality();
  const [modality, setModality] = useState<Modality>(initMod);
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  return (
    <Layout
      page={page}
      modality={modality}
      onModalityChange={setModality}
      favoritesOnly={favoritesOnly}
      onFavoritesChange={setFavoritesOnly}
    >
      <Routes>
        <Route
          path="/tasks"
          element={
            <TasksPage modality={modality} favoritesOnly={favoritesOnly} />
          }
        />
        <Route
          path="/query"
          element={
            <QueryPage modality={modality} favoritesOnly={favoritesOnly} />
          }
        />
        <Route
          path="/daily"
          element={
            <DailyPage modality={modality} favoritesOnly={favoritesOnly} />
          }
        />
        <Route
          path="/queue"
          element={
            <QueuePage />
          }
        />
        <Route
          path="/matrix"
          element={
            <MatrixPage />
          }
        />
        <Route
          path="/music"
          element={
            <MusicPage />
          }
        />
        <Route
          path="/voices"
          element={
            <VoicePage />
          }
        />
        <Route path="*" element={<Navigate to="/tasks" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
