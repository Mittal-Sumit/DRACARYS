import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

export async function generateProposal(query) {
  const { data } = await client.post("/generate-proposal/", { query });
  return data;
}
