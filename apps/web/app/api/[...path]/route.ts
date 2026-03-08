import type { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

const HEADER_ENV_MAP = [
  ['X-Dev-User-Id', 'MEAL_PLANNER_DEV_USER_ID'],
  ['X-Dev-User-Email', 'MEAL_PLANNER_DEV_USER_EMAIL'],
  ['X-Dev-User-Name', 'MEAL_PLANNER_DEV_USER_NAME'],
  ['X-Dev-Active-Household-Id', 'MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_ID'],
  ['X-Dev-Active-Household-Name', 'MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_NAME'],
  ['X-Dev-Active-Household-Role', 'MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_ROLE'],
  ['X-Dev-Households', 'MEAL_PLANNER_DEV_HOUSEHOLDS'],
] as const;

function configuredValue(value: string | undefined): string | undefined {
  const nextValue = value?.trim();
  return nextValue ? nextValue : undefined;
}

function resolveApiBaseUrl(): string {
  return (
    configuredValue(process.env.API_BASE_URL) ??
    configuredValue(process.env.NEXT_PUBLIC_API_BASE_URL) ??
    'http://localhost:8000'
  ).replace(/\/$/, '');
}

function buildUpstreamHeaders(request: NextRequest): Headers {
  const headers = new Headers(request.headers);
  headers.delete('host');

  for (const [headerName, envName] of HEADER_ENV_MAP) {
    const value = configuredValue(process.env[envName]);
    if (value) {
      headers.set(headerName, value);
    }
  }

  return headers;
}

async function proxy(request: NextRequest): Promise<Response> {
  const upstream = await fetch(`${resolveApiBaseUrl()}${request.nextUrl.pathname}${request.nextUrl.search}`, {
    method: request.method,
    headers: buildUpstreamHeaders(request),
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer(),
    cache: 'no-store',
    redirect: 'manual',
  });

  const headers = new Headers(upstream.headers);
  headers.delete('content-length');

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
