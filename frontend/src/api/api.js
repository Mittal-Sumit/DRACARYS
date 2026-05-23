import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

const isConnectionError = (err) =>
  !err.response || err.response.status === 502 || err.response.status === 503;

export async function generateProposal(query) {
  const MAX_RETRIES = 2;
  const RETRY_DELAY_MS = 800;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const { data } = await client.post("/generate-proposal/", { query });
      return data;
    } catch (err) {
      if (isConnectionError(err) && attempt < MAX_RETRIES) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
      throw err;
    }
  }
}
