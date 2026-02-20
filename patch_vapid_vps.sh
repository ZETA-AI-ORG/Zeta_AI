#!/bin/bash
# ─── Patch VAPID keys in .env on VPS ───
# Run this on your VPS: bash patch_vapid_vps.sh

# Remove any existing VAPID lines
sed -i '/^VAPID_/d' .env

# Add VAPID public key and subject
echo 'VAPID_PUBLIC_KEY=BLcH-mOSu1jREkMo2AANyGHChn9KTT3B_3KB6wSdKIbzB08X9joHsmgG_asEwcEwQkS8cUJZIRX4G2Fwf4aQAdE' >> .env
echo 'VAPID_CLAIMS_EMAIL=mailto:admin@zetaapp.xyz' >> .env

# Add VAPID private key (PEM format, multiline)
cat >> .env << 'VAPID_EOF'
VAPID_PRIVATE_KEY=-----BEGIN EC PRIVATE KEY-----
MHcCAQEEICOLCM1D9Eric84bhCmo2YT5rUdRvSms2Ayfj616fJsioAoGCCqGSM49
AwEHoUQDQgAEtwf6Y5K7WNESQyjYAA3IYcKGf0pNPcH/coHrBJ0ohvMHTxf2Ogey
aAb9qwTBwTBCRLxxQlkhFfgbYXB/hpAB0Q==
-----END EC PRIVATE KEY-----
VAPID_EOF

echo "✅ VAPID keys added to .env"
echo ""
echo "Verifying:"
grep "VAPID_" .env

echo ""
echo "Now restart your backend:"
echo "  systemctl restart zeta-backend"
echo "  # or: pm2 restart all"
