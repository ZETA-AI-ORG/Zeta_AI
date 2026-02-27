// ============================================
// ZETA PARTNER — Page de connexion
// ============================================
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Zap } from "lucide-react";

const PartnerLogin = () => {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email || !password) return;
    setLoading(true);
    setError("");
    try {
      await signIn(email, password);
      navigate("/partner");
    } catch (err: any) {
      setError(err.message ?? "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100dvh",
      background: "#EDEAE3",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px",
      fontFamily: "DM Sans, sans-serif",
    }}>
      <div style={{ marginBottom: "32px", textAlign: "center" }}>
        <div style={{
          width: "60px", height: "60px", background: "#1A1A1A",
          borderRadius: "18px", display: "flex", alignItems: "center",
          justifyContent: "center", margin: "0 auto 12px",
        }}>
          <Zap size={28} color="#fff" fill="#fff" />
        </div>
        <div style={{ fontFamily: "Saira, sans-serif", fontStyle: "italic", fontWeight: 800, fontSize: "22px" }}>
          ZETA PARTNER
        </div>
        <div style={{ fontSize: "13px", color: "#888", marginTop: "4px" }}>
          Connexion livreur
        </div>
      </div>

      <div style={{
        background: "#fff", borderRadius: "20px", padding: "24px",
        width: "100%", maxWidth: "380px", boxShadow: "0 4px 24px rgba(0,0,0,.06)",
      }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={{
            width: "100%", border: "1.5px solid #E8E5DE", borderRadius: "12px",
            padding: "14px", fontSize: "15px", marginBottom: "12px",
            fontFamily: "DM Sans, sans-serif", boxSizing: "border-box",
          }}
        />
        <input
          type="password"
          placeholder="Mot de passe"
          value={password}
          onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === "Enter" && void handleSubmit()}
          style={{
            width: "100%", border: "1.5px solid #E8E5DE", borderRadius: "12px",
            padding: "14px", fontSize: "15px", marginBottom: "16px",
            fontFamily: "DM Sans, sans-serif", boxSizing: "border-box",
          }}
        />
        {error && (
          <div style={{ color: "#D32F2F", fontSize: "13px", marginBottom: "12px", textAlign: "center" }}>
            {error}
          </div>
        )}
        <button
          onClick={() => void handleSubmit()}
          disabled={loading}
          style={{
            width: "100%", background: "#1A1A1A", color: "#fff",
            border: "none", borderRadius: "12px", padding: "16px",
            fontFamily: "Saira, sans-serif", fontStyle: "italic",
            fontWeight: 800, fontSize: "16px", cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Connexion…" : "Se connecter"}
        </button>
      </div>
    </div>
  );
};

export default PartnerLogin;