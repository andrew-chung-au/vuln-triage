import { mockServices } from './mockServices';
import type { VulnTriageServices } from './types';

// Central seam. The whole app imports `services` and calls through it.
// Swap this binding to point at a real API implementation later.
export const services: VulnTriageServices = mockServices;
