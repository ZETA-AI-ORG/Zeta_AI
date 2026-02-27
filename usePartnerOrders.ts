// ============================================
// ZETA PARTNER — usePartnerOrders
// Commandes disponibles + Mes livraisons
// Temps réel via Supabase Realtime
// ============================================
import { useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/contexts/AuthContext";
import type { OrderDelivery, DeliveryStatus } from "@/types/partner";

const QUERY_KEYS = {
  openOrders: ["partner", "open-orders"],
  myDeliveries: (userId: string) => ["partner", "my-deliveries", userId],
};

// ── Commandes disponibles (status = 'open', pas encore assignées) ──
const fetchOpenOrders = async (): Promise<OrderDelivery[]> => {
  const { data, error } = await supabase
    .from("order_deliveries")
    .select(`
      *,
      orders (
        id,
        company_id,
        customer_name,
        customer_phone,
        delivery_zone,
        delivery_address,
        items,
        total_amount,
        created_at
      )
    `)
    .eq("status", "open")
    .is("partner_id", null)
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) throw error;
  return (data ?? []) as OrderDelivery[];
};

// ── Mes livraisons (assignées à ce livreur, statuts actifs) ──
const fetchMyDeliveries = async (partnerId: string): Promise<OrderDelivery[]> => {
  const { data, error } = await supabase
    .from("order_deliveries")
    .select(`
      *,
      orders (
        id,
        company_id,
        customer_name,
        customer_phone,
        delivery_zone,
        delivery_address,
        items,
        total_amount,
        created_at
      )
    `)
    .eq("partner_id", partnerId)
    .in("status", ["accepted", "picked_up", "postponed"])
    .order("created_at", { ascending: false });

  if (error) throw error;
  return (data ?? []) as OrderDelivery[];
};

export const usePartnerOrders = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // ── Queries ──
  const {
    data: openOrders = [],
    isLoading: isLoadingOrders,
    refetch: refetchOrders,
  } = useQuery({
    queryKey: QUERY_KEYS.openOrders,
    queryFn: fetchOpenOrders,
    refetchInterval: 30_000, // fallback polling toutes les 30s
    staleTime: 10_000,
  });

  const {
    data: myDeliveries = [],
    isLoading: isLoadingDeliveries,
  } = useQuery({
    queryKey: QUERY_KEYS.myDeliveries(user?.id ?? ""),
    queryFn: () => fetchMyDeliveries(user!.id),
    enabled: !!user?.id,
    refetchInterval: 30_000,
    staleTime: 10_000,
  });

  // ── Realtime — nouvelles commandes ──
  useEffect(() => {
    const channel = supabase
      .channel("open-orders-realtime")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "order_deliveries",
          filter: "status=eq.open",
        },
        () => {
          void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.openOrders });
        }
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [queryClient]);

  // ── Realtime — mes livraisons ──
  useEffect(() => {
    if (!user?.id) return;
    const channel = supabase
      .channel(`my-deliveries-${user.id}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "order_deliveries",
          filter: `partner_id=eq.${user.id}`,
        },
        () => {
          void queryClient.invalidateQueries({
            queryKey: QUERY_KEYS.myDeliveries(user.id),
          });
          void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.openOrders });
        }
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [user?.id, queryClient]);

  // ── Mutation: Accepter une commande ──
  const acceptOrder = useMutation({
    mutationFn: async ({ deliveryId }: { deliveryId: string }) => {
      if (!user?.id) throw new Error("Non authentifié");
      const { error } = await supabase
        .from("order_deliveries")
        .update({
          status: "accepted" as DeliveryStatus,
          partner_id: user.id,
          updated_at: new Date().toISOString(),
        })
        .eq("id", deliveryId)
        .eq("status", "open"); // sécurité: seulement si encore open

      if (error) throw error;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.openOrders });
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.myDeliveries(user?.id ?? ""),
      });
    },
  });

  // ── Mutation: Mettre à jour le statut d'une livraison ──
  const updateDeliveryStatus = useMutation({
    mutationFn: async ({
      deliveryId,
      status,
      scheduledDate,
      cancellationReason,
    }: {
      deliveryId: string;
      status: DeliveryStatus;
      scheduledDate?: string;
      cancellationReason?: string;
    }) => {
      const updates: Record<string, unknown> = {
        status,
        updated_at: new Date().toISOString(),
      };
      if (scheduledDate) updates.scheduled_date = scheduledDate;
      if (cancellationReason) updates.cancellation_reason = cancellationReason;

      const { error } = await supabase
        .from("order_deliveries")
        .update(updates)
        .eq("id", deliveryId);

      if (error) throw error;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.myDeliveries(user?.id ?? ""),
      });
    },
  });

  const refetchOrdersCallback = useCallback(() => {
    void refetchOrders();
  }, [refetchOrders]);

  return {
    openOrders,
    myDeliveries,
    isLoadingOrders,
    isLoadingDeliveries,
    acceptOrder,
    updateDeliveryStatus,
    refetchOrders: refetchOrdersCallback,
  };
};