// Single entry point for all backend calls. Swap mockServices for a real
// API-backed implementation of the same Services interface later.
import { DEMO_CREDENTIALS } from "./mockData";
import { mockServices } from "./mockService";
import type { Services } from "./types";

export const services: Services = mockServices;

/** Demo credentials are data the login screen needs without importing the mock. */
export const demoCredentials = DEMO_CREDENTIALS;

export * from "./types";
