// ============================================
// ZETA PARTNER — main.tsx
// ============================================
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import PartnerCommandesV2 from "@/pages/PartnerCommandesV2";
import PartnerLogin from "@/pages/PartnerLogin";
import { Toaster } from "@/components/ui/toaster";
import "@/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

// Route protégée
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/partner/login" replace />;
  return <>{children}</>;
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/partner/login" element={<PartnerLogin />} />
            <Route
              path="/partner/*"
              element={
                <ProtectedRoute>
                  <PartnerCommandesV2 />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/partner" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);