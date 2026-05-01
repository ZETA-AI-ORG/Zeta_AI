import { useState, useEffect } from "react";

const FCFA_RATE = 615;
const YOUR_MARGIN = 1500; // FCFA marge par an

const PLANS = [
  {
    id: "free",
    label: "Gratuit",
    badge: "INCLUS",
    badgeColor: "#00E5A0",
    tagline: "Commencer sans rien payer",
    url: (slug) => `myzeta.xyz/shop/${slug}`,
    priceYear: 0,
    renewYear: 0,
    features: ["Sous-domaine myZeta", "SSL inclus", "Activé instantanément"],
    cta: "Utiliser gratuitement",
    popular: false,
  },
  {
    id: "xyz",
    label: ".xyz",
    badge: "POPULAIRE",
    badgeColor: "#7C6FFF",
    tagline: "Domaine personnel pas cher",
    url: (slug) => `${slug}.xyz`,
    priceYear: Math.round(2.04 * FCFA_RATE + YOUR_MARGIN),
    renewYear: Math.round(12.98 * FCFA_RATE + YOUR_MARGIN),
    features: ["Votre propre domaine", "SSL automatique", "Config DNS auto"],
    cta: "Choisir .xyz",
    popular: true,
  },
  {
    id: "shop",
    label: ".shop",
    badge: "E-COMMERCE",
    badgeColor: "#FF6B35",
    tagline: "L'extension dédiée aux boutiques",
    url: (slug) => `${slug}.shop`,
    priceYear: Math.round(2.06 * FCFA_RATE + YOUR_MARGIN),
    renewYear: Math.round(31.41 * FCFA_RATE + YOUR_MARGIN),
    features: ["Extension boutique", "SSL automatique", "Config DNS auto"],
    cta: "Choisir .shop",
    popular: false,
  },
];

function formatFCFA(n) {
  return n.toLocaleString("fr-FR") + " FCFA";
}

export default function DomainPage() {
  const [slug, setSlug] = useState("restaubienaimer");
  const [selected, setSelected] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [checking, setChecking] = useState(false);
  const [available, setAvailable] = useState(null);
  const [step, setStep] = useState("choose"); // choose | confirm | success

  useEffect(() => {
    if (selected && selected.id !== "free") {
      setChecking(true);
      setAvailable(null);
      const t = setTimeout(() => {
        setAvailable(Math.random() > 0.2);
        setChecking(false);
      }, 1200);
      return () => clearTimeout(t);
    }
  }, [selected, slug]);

  const handleConfirm = () => {
    setStep("success");
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0A0A0F",
      fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
      color: "#fff",
      padding: "0",
      overflowX: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .card { transition: all 0.25s cubic-bezier(0.4,0,0.2,1); }
        .card:hover { transform: translateY(-3px); }
        .card.selected { transform: translateY(-3px); }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .slide-in { animation: slideIn 0.4s ease forwards; }
        @keyframes slideIn { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
        input:focus { outline: none; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #111; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
      `}</style>

      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #0A0A0F 0%, #12102A 100%)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "20px 24px",
        display: "flex",
        alignItems: "center",
        gap: "12px",
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: "10px",
          background: "linear-gradient(135deg, #7C6FFF, #00E5A0)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "16px", fontWeight: 800,
        }}>M</div>
        <div>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: "15px" }}>myZeta</div>
          <div style={{ fontSize: "11px", color: "#666" }}>Gestion de boutique</div>
        </div>
      </div>

      <div style={{ maxWidth: 480, margin: "0 auto", padding: "32px 20px 80px" }}>

        {step === "choose" && (
          <div className="slide-in">
            {/* Title */}
            <div style={{ marginBottom: "32px" }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "rgba(124,111,255,0.12)", borderRadius: "20px",
                padding: "4px 12px", marginBottom: "14px",
                border: "1px solid rgba(124,111,255,0.2)",
              }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#7C6FFF" }} className="pulse" />
                <span style={{ fontSize: "11px", color: "#7C6FFF", letterSpacing: "0.08em", fontWeight: 600 }}>
                  DOMAINE & ADRESSE
                </span>
              </div>
              <h1 style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontSize: "26px", fontWeight: 800, lineHeight: 1.2, marginBottom: "8px",
              }}>
                Choisissez votre<br />
                <span style={{ background: "linear-gradient(90deg,#7C6FFF,#00E5A0)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                  adresse web
                </span>
              </h1>
              <p style={{ fontSize: "14px", color: "#888", lineHeight: 1.6 }}>
                Prix en temps réel — vous pouvez changer à tout moment.
              </p>
            </div>

            {/* Slug input */}
            <div style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "14px",
              padding: "16px",
              marginBottom: "24px",
            }}>
              <div style={{ fontSize: "11px", color: "#666", letterSpacing: "0.06em", marginBottom: "8px", fontWeight: 600 }}>
                NOM DE VOTRE BOUTIQUE
              </div>
              <input
                value={slug}
                onChange={e => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                style={{
                  width: "100%", background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px",
                  padding: "12px 14px", color: "#fff", fontSize: "16px", fontWeight: 600,
                  letterSpacing: "0.02em",
                }}
                placeholder="nomdelaboutique"
              />
              {selected && (
                <div style={{
                  marginTop: "10px", fontSize: "13px", color: "#00E5A0",
                  fontWeight: 500,
                }}>
                  → {selected.url(slug)}
                </div>
              )}
            </div>

            {/* Plans */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {PLANS.map(plan => {
                const isSelected = selected?.id === plan.id;
                return (
                  <div
                    key={plan.id}
                    className={`card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelected(plan)}
                    style={{
                      background: isSelected
                        ? `linear-gradient(135deg, rgba(124,111,255,0.12), rgba(0,229,160,0.06))`
                        : "rgba(255,255,255,0.03)",
                      border: isSelected
                        ? "1px solid rgba(124,111,255,0.5)"
                        : "1px solid rgba(255,255,255,0.07)",
                      borderRadius: "16px",
                      padding: "18px",
                      cursor: "pointer",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    {/* Badge */}
                    <div style={{
                      position: "absolute", top: 14, right: 14,
                      background: plan.badgeColor + "22",
                      border: `1px solid ${plan.badgeColor}44`,
                      borderRadius: "8px", padding: "2px 8px",
                      fontSize: "10px", fontWeight: 700, color: plan.badgeColor,
                      letterSpacing: "0.06em",
                    }}>
                      {plan.badge}
                    </div>

                    <div style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
                      {/* Radio */}
                      <div style={{
                        width: 20, height: 20, borderRadius: "50%", marginTop: "2px",
                        border: isSelected ? "2px solid #7C6FFF" : "2px solid #333",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        flexShrink: 0, transition: "all 0.2s",
                      }}>
                        {isSelected && <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#7C6FFF" }} />}
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "3px" }}>
                          <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: "18px", fontWeight: 800 }}>
                            {plan.label}
                          </span>
                          <span style={{ fontSize: "12px", color: "#666" }}>{plan.tagline}</span>
                        </div>

                        {/* URL preview */}
                        <div style={{
                          fontSize: "12px", color: plan.badgeColor, fontWeight: 600,
                          marginBottom: "12px", opacity: 0.9,
                        }}>
                          {plan.url(slug || "votreboutique")}
                        </div>

                        {/* Pricing */}
                        {plan.priceYear === 0 ? (
                          <div style={{
                            display: "inline-flex", alignItems: "center", gap: "6px",
                            background: "rgba(0,229,160,0.1)", borderRadius: "8px",
                            padding: "6px 12px",
                          }}>
                            <span style={{ fontSize: "20px", fontWeight: 800, color: "#00E5A0" }}>0 FCFA</span>
                            <span style={{ fontSize: "11px", color: "#00E5A0", opacity: 0.7 }}>pour toujours</span>
                          </div>
                        ) : (
                          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                            <div style={{
                              background: "rgba(255,255,255,0.05)", borderRadius: "10px",
                              padding: "8px 12px",
                            }}>
                              <div style={{ fontSize: "10px", color: "#666", marginBottom: "2px" }}>1ÈRE ANNÉE</div>
                              <div style={{ fontSize: "16px", fontWeight: 700, color: plan.badgeColor }}>
                                {formatFCFA(plan.priceYear)}
                              </div>
                            </div>
                            <div style={{
                              background: "rgba(255,255,255,0.05)", borderRadius: "10px",
                              padding: "8px 12px",
                            }}>
                              <div style={{ fontSize: "10px", color: "#666", marginBottom: "2px" }}>RENOUVELLEMENT</div>
                              <div style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>
                                {formatFCFA(plan.renewYear)}/an
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Features */}
                        <div style={{ marginTop: "12px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {plan.features.map(f => (
                            <span key={f} style={{
                              fontSize: "11px", color: "#888",
                              background: "rgba(255,255,255,0.04)",
                              borderRadius: "6px", padding: "3px 8px",
                              border: "1px solid rgba(255,255,255,0.06)",
                            }}>✓ {f}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Availability check */}
            {selected && selected.id !== "free" && (
              <div className="slide-in" style={{
                marginTop: "16px",
                background: "rgba(255,255,255,0.04)",
                borderRadius: "12px", padding: "14px 16px",
                border: "1px solid rgba(255,255,255,0.07)",
                display: "flex", alignItems: "center", gap: "10px",
              }}>
                {checking ? (
                  <>
                    <div className="spin" style={{
                      width: 16, height: 16, border: "2px solid #333",
                      borderTopColor: "#7C6FFF", borderRadius: "50%",
                    }} />
                    <span style={{ fontSize: "13px", color: "#888" }}>
                      Vérification de <strong style={{ color: "#fff" }}>{selected.url(slug)}</strong>…
                    </span>
                  </>
                ) : available ? (
                  <>
                    <div style={{ width: 16, height: 16, borderRadius: "50%", background: "#00E5A0", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px" }}>✓</div>
                    <span style={{ fontSize: "13px", color: "#00E5A0", fontWeight: 600 }}>
                      {selected.url(slug)} est disponible !
                    </span>
                  </>
                ) : (
                  <>
                    <div style={{ width: 16, height: 16, borderRadius: "50%", background: "#FF4757", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px" }}>✕</div>
                    <span style={{ fontSize: "13px", color: "#FF4757" }}>
                      Indisponible — essayez un autre nom
                    </span>
                  </>
                )}
              </div>
            )}

            {/* CTA */}
            <button
              onClick={() => selected && (selected.id === "free" || available) && setStep("confirm")}
              disabled={!selected || (selected.id !== "free" && (checking || !available))}
              style={{
                width: "100%", marginTop: "24px",
                padding: "16px",
                background: selected && (selected.id === "free" || available)
                  ? "linear-gradient(135deg, #7C6FFF, #5A4FD4)"
                  : "rgba(255,255,255,0.06)",
                border: "none", borderRadius: "14px",
                color: selected && (selected.id === "free" || available) ? "#fff" : "#444",
                fontSize: "15px", fontWeight: 700,
                cursor: selected && (selected.id === "free" || available) ? "pointer" : "not-allowed",
                transition: "all 0.2s",
                letterSpacing: "0.02em",
              }}
            >
              {!selected ? "Sélectionnez un plan" : selected.cta} →
            </button>
          </div>
        )}

        {step === "confirm" && selected && (
          <div className="slide-in">
            <button onClick={() => setStep("choose")} style={{
              background: "none", border: "none", color: "#666",
              fontSize: "13px", cursor: "pointer", marginBottom: "24px",
              display: "flex", alignItems: "center", gap: "6px",
            }}>← Retour</button>

            <h2 style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: "22px", fontWeight: 800, marginBottom: "6px",
            }}>Confirmer votre domaine</h2>
            <p style={{ fontSize: "14px", color: "#888", marginBottom: "28px" }}>
              Vérifiez les détails avant de valider.
            </p>

            {/* Summary card */}
            <div style={{
              background: "rgba(124,111,255,0.08)",
              border: "1px solid rgba(124,111,255,0.3)",
              borderRadius: "16px", padding: "20px",
              marginBottom: "20px",
            }}>
              <div style={{ fontSize: "11px", color: "#7C6FFF", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "16px" }}>
                RÉCAPITULATIF
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#888", fontSize: "13px" }}>Domaine</span>
                  <span style={{ fontWeight: 700, color: "#00E5A0", fontSize: "14px" }}>{selected.url(slug)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#888", fontSize: "13px" }}>Aujourd'hui</span>
                  <span style={{ fontWeight: 700, fontSize: "14px" }}>
                    {selected.priceYear === 0 ? "Gratuit" : formatFCFA(selected.priceYear)}
                  </span>
                </div>
                {selected.renewYear > 0 && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#888", fontSize: "13px" }}>Renouvellement annuel</span>
                    <span style={{ color: "#888", fontSize: "14px" }}>{formatFCFA(selected.renewYear)}</span>
                  </div>
                )}
                <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: "12px", display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#888", fontSize: "13px" }}>SSL & Config DNS</span>
                  <span style={{ color: "#00E5A0", fontSize: "13px", fontWeight: 600 }}>Automatique ✓</span>
                </div>
              </div>
            </div>

            <div style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: "12px", padding: "14px",
              marginBottom: "20px", fontSize: "13px", color: "#666", lineHeight: 1.6,
            }}>
              ℹ️ Après confirmation, votre domaine sera actif dans <strong style={{ color: "#fff" }}>2 à 5 minutes</strong>. Le certificat SSL sera généré automatiquement.
            </div>

            <button
              onClick={handleConfirm}
              style={{
                width: "100%", padding: "16px",
                background: "linear-gradient(135deg, #00E5A0, #00B87A)",
                border: "none", borderRadius: "14px",
                color: "#0A0A0F", fontSize: "15px", fontWeight: 800,
                cursor: "pointer", letterSpacing: "0.02em",
              }}
            >
              {selected.priceYear === 0 ? "Activer gratuitement" : `Payer ${formatFCFA(selected.priceYear)} →`}
            </button>
          </div>
        )}

        {step === "success" && (
          <div className="slide-in" style={{ textAlign: "center", paddingTop: "40px" }}>
            <div style={{
              width: 80, height: 80, borderRadius: "50%",
              background: "linear-gradient(135deg, #00E5A0, #00B87A)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "36px", margin: "0 auto 24px",
              boxShadow: "0 0 40px rgba(0,229,160,0.3)",
            }}>✓</div>
            <h2 style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: "24px", fontWeight: 800, marginBottom: "8px",
            }}>Domaine activé !</h2>
            <p style={{ fontSize: "14px", color: "#888", marginBottom: "32px", lineHeight: 1.6 }}>
              Votre boutique est accessible à :<br />
              <strong style={{ color: "#00E5A0", fontSize: "16px" }}>{selected?.url(slug)}</strong>
            </p>
            <div style={{
              background: "rgba(255,255,255,0.04)", borderRadius: "14px",
              padding: "16px", marginBottom: "28px",
              border: "1px solid rgba(255,255,255,0.07)",
            }}>
              <div style={{ fontSize: "11px", color: "#666", marginBottom: "12px", letterSpacing: "0.06em", fontWeight: 600 }}>
                PROCHAINES ÉTAPES
              </div>
              {["SSL en cours de génération (2-5 min)", "DNS configuré automatiquement", "Boutique en ligne"].map((s, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: "10px",
                  padding: "8px 0",
                  borderBottom: i < 2 ? "1px solid rgba(255,255,255,0.05)" : "none",
                }}>
                  <div style={{
                    width: 20, height: 20, borderRadius: "50%",
                    background: i === 2 ? "#00E5A0" : "rgba(124,111,255,0.2)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "10px", color: i === 2 ? "#0A0A0F" : "#7C6FFF",
                  }}>{i === 2 ? "✓" : <div className="pulse" style={{ width: 6, height: 6, borderRadius: "50%", background: "#7C6FFF" }} />}</div>
                  <span style={{ fontSize: "13px", color: i === 2 ? "#fff" : "#888" }}>{s}</span>
                </div>
              ))}
            </div>
            <button
              onClick={() => { setStep("choose"); setSelected(null); setAvailable(null); }}
              style={{
                background: "none", border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px", padding: "12px 24px",
                color: "#888", fontSize: "13px", cursor: "pointer",
              }}
            >Gérer un autre domaine</button>
          </div>
        )}
      </div>
    </div>
  );
}