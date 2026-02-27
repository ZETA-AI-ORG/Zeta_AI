// ============================================
// ZETA PARTNER — usePartnerStats
// Stats du jour pour le Dashboard
// ============================================
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/contexts/AuthContext";
import type { PartnerStats } from "@/types/partner";

const fetchStats = async (partnerId: string): Promise<PartnerStats> => {
  // Début de la journée locale en UTC
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayISO = today.toISOString();

  const { data, error } = await supabase
    .from("order_deliveries")
    .select(`
      status,
      orders ( total_amount )
    `)
    .eq("partner_id", partnerId)
    .gte("created_at", todayISO);

  if (error) throw error;

  const deliveries = data ?? [];

  const delivered = deliveries.filter(d => d.status === "delivered").length;
  const accepted = deliveries.filter(d =>
    ["accepted", "picked_up", "delivered"].includes(d.status)
  ).length;
  const cancelled = deliveries.filter(d => d.status === "cancelled").length;
  const postponed = deliveries.filter(d => d.status === "postponed").length;

  const revenue = deliveries
    .filter(d => d.status === "delivered")
    .reduce((sum, d) => {
      const order = d.orders as { total_amount?: number } | null;
      return sum + (order?.total_amount ?? 0);
    }, 0);

  const total = delivered + cancelled;
  const successRate = total > 0 ? Math.round((delivered / total) * 100) : 0;

  return { delivered, accepted, cancelled, postponed, revenue, successRate };
};

export const usePartnerStats = () => {
  const { user } = useAuth();

  return useQuery<PartnerStats>({
    queryKey: ["partner", "stats", user?.id, new Date().toDateString()],
    queryFn: () => fetchStats(user!.id),
    enabled: !!user?.id,
    refetchInterval: 60_000, // rafraîchit toutes les minutes
    staleTime: 30_000,
  });
};