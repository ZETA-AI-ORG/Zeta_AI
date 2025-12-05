const { Client, LocalAuth } = require("whatsapp-web.js");
const QRCode = require("qrcode");
const fs = require("fs");

// Initialisation du client WhatsApp
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Événement QR : génération et sauvegarde dans un fichier
client.on("qr", async (qr) => {
    try {
        await QRCode.toFile("whatsapp_qr.png", qr, { width: 300 });
        console.log("✅ QR code généré et sauvegardé : whatsapp_qr.png");
        console.log("�� Scanne ce QR avec ton WhatsApp Business pour te connecter.");
    } catch (err) {
        console.error("❌ Erreur lors de la génération du QR code :", err);
    }
});

// Événement ready : extraction des conversations
client.on("ready", async () => {
    console.log("💚 Connecté ! Extraction de toutes les conversations…");

    let allData = [];

    const chats = await client.getChats();
    console.log(`📦 Conversations trouvées : ${chats.length}`);

    for (let chat of chats) {
        console.log(`➡️ Extraction : ${chat.name || chat.id.user}`);

        let messages = await chat.fetchMessages({ limit: 5000 });

        allData.push({
            chatName: chat.name || null,
            chatId: chat.id._serialized,
            isGroup: chat.isGroup,
            messages: messages.map(m => ({
                _id: m.id.id,
                from: m.from,
                to: m.to,
                body: m.body,
                timestamp: m.timestamp,
                type: m.type
            }))
        });
    }

    fs.writeFileSync("whatsapp_export.json", JSON.stringify(allData, null, 2));
    console.log("✅ EXPORT TERMINÉ : whatsapp_export.json");
    process.exit(0);
});

// Lancement du client
client.initialize();

