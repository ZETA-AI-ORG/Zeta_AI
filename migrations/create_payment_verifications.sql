-- ═══════════════════════════════════════════════════════════════
-- Table: payment_verifications
-- Anti-replay + audit trail for receipt verification via Gemini
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS payment_verifications (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  company_id      UUID NOT NULL,

  -- Session context (sent from frontend)
  payment_session_id  TEXT,
  offer_type          TEXT CHECK (offer_type IN ('topup', 'subscription')),
  plan_id             TEXT,
  expected_amount     INTEGER,
  expected_merchant   TEXT DEFAULT 'ZETA',

  -- Timing
  pay_clicked_at      TIMESTAMPTZ,
  uploaded_at         TIMESTAMPTZ DEFAULT now(),
  delay_seconds       INTEGER,

  -- OCR / Gemini extraction
  transaction_id      TEXT,
  transaction_id_suffix TEXT,
  receipt_amount      INTEGER,
  receipt_merchant    TEXT,
  receipt_datetime    TIMESTAMPTZ,
  receipt_status      TEXT,
  receipt_sender      TEXT,
  receipt_fees        INTEGER,

  -- Anti-replay keys
  image_hash          TEXT,

  -- Gemini raw payload
  gemini_payload      JSONB,

  -- Verdict
  decision            TEXT NOT NULL CHECK (decision IN ('approved', 'manual_review', 'rejected')),
  decision_reasons    TEXT[],
  risk_score          REAL DEFAULT 0,
  confidence          REAL DEFAULT 0,

  -- Proof URL in storage
  proof_url           TEXT,

  created_at          TIMESTAMPTZ DEFAULT now()
);

-- Anti-replay: same transaction ID can't be reused
CREATE UNIQUE INDEX IF NOT EXISTS idx_pv_transaction_id
  ON payment_verifications (transaction_id)
  WHERE transaction_id IS NOT NULL;

-- Anti-replay: same image can't be reused
CREATE UNIQUE INDEX IF NOT EXISTS idx_pv_image_hash
  ON payment_verifications (image_hash)
  WHERE image_hash IS NOT NULL;

-- Composite anti-replay: tx suffix + amount + merchant
CREATE UNIQUE INDEX IF NOT EXISTS idx_pv_suffix_amount_merchant
  ON payment_verifications (transaction_id_suffix, receipt_amount, receipt_merchant)
  WHERE transaction_id_suffix IS NOT NULL;

-- Lookup by company
CREATE INDEX IF NOT EXISTS idx_pv_company_id ON payment_verifications (company_id);

-- Lookup by session
CREATE INDEX IF NOT EXISTS idx_pv_session ON payment_verifications (payment_session_id);

-- RLS
ALTER TABLE payment_verifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Backend inserts payment verifications"
  ON payment_verifications FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Users read own payment verifications"
  ON payment_verifications FOR SELECT
  USING (company_id = auth.uid());
