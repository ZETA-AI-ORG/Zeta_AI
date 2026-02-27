// ============================================
// ZETA PARTNER — Types Supabase
// ============================================

export type DeliveryStatus =
  | "open"
  | "accepted"
  | "picked_up"
  | "delivered"
  | "postponed"
  | "cancelled";

export interface OrderItem {
  name?: string;
  product?: string;
  quantity?: number;
  price?: number;
}

export interface Order {
  id: string;
  company_id: string;
  customer_name: string | null;
  customer_phone: string | null;
  delivery_zone: string | null;
  delivery_address: string | null;
  items: OrderItem[] | string | null;
  total_amount: number;
  created_at: string;
}

export interface OrderDelivery {
  id: string;
  order_id: string;
  partner_id: string | null;
  status: DeliveryStatus;
  scheduled_date: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string | null;
  orders?: Order;
}

export interface PartnerStats {
  delivered: number;
  accepted: number;
  cancelled: number;
  postponed: number;
  revenue: number;
  successRate: number;
}

export interface ArchiveDay {
  date: string;
  label: string;
  delivered: number;
  cancelled: number;
  revenue: number;
  deliveries: OrderDelivery[];
}

export interface PartnerProfile {
  id: string;
  user_id: string;
  company_name: string | null;
  full_name: string | null;
  phone: string | null;
  whatsapp: string | null;
  email: string | null;
  vehicle_type: string | null;
  vehicle_plate: string | null;
  zones: string[] | null;
  matricule: string | null;
  cni: string | null;
  verified: boolean;
}