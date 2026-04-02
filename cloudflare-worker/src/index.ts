export interface Env {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  BUCKET: any;
  UPLOAD_SECRET: string;
  CDN_URL: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "X-Upload-Token, Content-Type",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    if (request.method !== "POST") {
      return Response.json({ error: "Method not allowed" }, { status: 405 });
    }

    const token = request.headers.get("X-Upload-Token");
    if (!token || token !== env.UPLOAD_SECRET) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
      const formData = await request.formData();
      const file = formData.get("file");

      if (!file || !(file instanceof File)) {
        return Response.json({ error: "No file provided" }, { status: 400 });
      }

      const ext = file.name.split(".").pop() || "webp";
      const key = `products/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;

      await env.BUCKET.put(key, file.stream(), {
        httpMetadata: {
          contentType: file.type || "image/webp",
          cacheControl: "public, max-age=31536000, immutable",
        },
      });

      const cdnBase = env.CDN_URL || "https://img.myzeta.xyz";
      const url = `${cdnBase}/${key}`;

      return Response.json({ url }, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Content-Type": "application/json",
        },
      });
    } catch (err: any) {
      return Response.json(
        { error: `Erreur serveur : ${err?.message || "Unknown"}` },
        { status: 500 }
      );
    }
  },
};
