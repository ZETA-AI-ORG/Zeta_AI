-- ═══════════════════════════════════════════════════════════════
-- payment_attempts — logs every verification attempt (success or fail)
-- Used for: duplicate detection (SHA-256 hash), rate limiting, debugging
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.payment_attempts (
    id           uuid         NOT NULL DEFAULT gen_random_uuid(),
    company_id   text         NOT NULL,
    file_hash    text         NOT NULL,
    file_name    text,
    file_size    integer,
    mime_type    text,
    status       text         DEFAULT 'pending',
    -- 'pending', 'processing', 'ocr_success', 'ocr_failed', 'duplicate', 'rate_limited', 'rejected'
    decision     text,
    raw_ocr_result jsonb,
    error_message  text,
    created_at   timestamptz  DEFAULT now(),

    CONSTRAINT payment_attempts_pkey PRIMARY KEY (id)
);

-- Fast duplicate lookup by hash
CREATE INDEX IF NOT EXISTS idx_payment_attempts_hash
    ON public.payment_attempts (file_hash);

-- Fast rate-limiting lookup by company_id + created_at
CREATE INDEX IF NOT EXISTS idx_payment_attempts_company_time
    ON public.payment_attempts (company_id, created_at DESC);

-- RLS: service role only (backend writes, no client access)
ALTER TABLE public.payment_attempts ENABLE ROW LEVEL SECURITY;
