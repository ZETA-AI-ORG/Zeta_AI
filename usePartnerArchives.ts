// ============================================
// ZETA PARTNER — usePartnerArchives
// Historique 7 jours, reset dim. 23h59
// ============================================
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/contexts/AuthContext";
import type { ArchiveDay, OrderDelivery } from "@/types/partner";

const JOURS = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
const MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

const formatDayLabel = (dateStr: string): string => {
  const d = new Date(dateStr);
  return `${JOURS[d.getDay()]} ${d.getDate()} ${MOIS[d.getMonth()]}`;
};

// Calcule le début de la semaine courante (lundi à minuit ou dernier dimanche 23h59)
const getArchiveStartDate = (): Date => {
  const now = new Date();
  const dayOfWeek = now.getDay(); // 0=dim, 1=lun...
  // On remonte à lundi 00:00 de la semaine courante
  const daysBack = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  const start = new Date(now);
  start.setDate(now.getDate() - daysBack);
  start.setHours(0, 0, 0, 0);
  return start;
};

const fetchArchives = async (partnerId: string): Promise<ArchiveDay[]> => {
  const startDate = getArchiveStartDate();

  const { data, error } = await supabase
    .from("order_deliveries")
    .select(`
      *,
      orders (
        id,
        customer_name,
        delivery_zone,
        items,
        total_amount,
        created_at
      )
    `)
    .eq("partner_id", partnerId)
    .in("status", ["delivered", "cancelled"])
    .gte("updated_at", startDate.toISOString())
    .order("updated_at", { ascending: false });

  if (error) throw error;

  const deliveries = (data ?? []) as OrderDelivery[];

  // Groupe par jour
  const byDay = new Map<string, OrderDelivery[]>();
  for (const delivery of deliveries) {
    const dateStr = new Date(delivery.updated_at ?? delivery.created_at)
      .toISOString()
      .slice(0, 10); // YYYY-MM-DD
    if (!byDay.has(dateStr)) byDay.set(dateStr, []);
    byDay.get(dateStr)!.push(delivery);
  }

  // Construit les jours triés du plus récent au plus ancien
  const archiveDays: ArchiveDay[] = Array.from(byDay.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, items]) => {
      const delivered = items.filter(d => d.status === "delivered").length;
      const cancelled = items.filter(d => d.status === "cancelled").length;
      const revenue = items
        .filter(d => d.status === "delivered")
        .reduce((sum, d) => sum + ((d.orders as any)?.total_amount ?? 0), 0);

      return {
        date,
        label: formatDayLabel(date),
        delivered,
        cancelled,
        revenue,
        deliveries: items,
      };
    });

  return archiveDays;
};

export const usePartnerArchives = () => {
  const { user } = useAuth();

  return useQuery<ArchiveDay[]>({
    queryKey: ["partner", "archives", user?.id],
    queryFn: () => fetchArchives(user!.id),
    enabled: !!user?.id,
    staleTime: 5 * 60_000, // 5 minutes — les archives changent peu
  });
};