// Single entry point for all backend calls.
//
// The app uses the real backend-backed service (httpServices). The mock stays
// exported for vitest fixtures only; it is no longer the production wiring
// (task 11 / #133). Every implementation satisfies the same Services interface.
import { httpServices } from "./httpService";
import { DEMO_CREDENTIALS } from "./mockData";
import type { Services } from "./types";

export const services: Services = httpServices;

/** The mock remains available as a test fixture, not as production wiring. */
export { mockServices } from "./mockService";

/** Demo credentials shown on the sign-in screen as a hint. */
export const demoCredentials = DEMO_CREDENTIALS;

export * from "./types";
