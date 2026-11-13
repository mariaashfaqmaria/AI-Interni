// frontend/src/api.js
import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 60000 });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    if (error.response?.status === 401 && !url.includes("/auth/login") && !url.includes("/auth/register")) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
    return Promise.reject(error);
  }
);

export const errorMessage = (error, fallback = "Something went wrong. Please try again.") => {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};

export default api;