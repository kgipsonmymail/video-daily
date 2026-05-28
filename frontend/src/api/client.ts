import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API Error:", err);
    return Promise.reject(err);
  }
);

export default client;
