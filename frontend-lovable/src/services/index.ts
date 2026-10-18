// Single entry point for all backend calls. Swap mockServices for a real
// API-backed implementation of the same Services interface later.
import { mockServices } from "./mockService";
import type { Services } from "./types";

export const services: Services = mockServices;
export * from "./types";
