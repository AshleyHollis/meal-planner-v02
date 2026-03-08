import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { fetchSession } from './session';

const originalFetch = globalThis.fetch;

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('fetchSession returns authenticated household context from bootstrap response', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(200, {
      authenticated: true,
      user: {
        user_id: 'user-123',
        email: 'ashley@example.com',
        display_name: 'Ashley',
        active_household_id: 'household-abc',
        households: [
          {
            household_id: 'household-abc',
            household_name: 'Primary Household',
            role: 'owner',
          },
        ],
      },
    });
  }) as typeof fetch;

  const session = await fetchSession();

  assert.equal(calls.length, 1);
  assert.equal(String(calls[0].input), '/api/v1/me');
  assert.equal(calls[0].init?.credentials, 'include');
  assert.equal(session.status, 'authenticated');
  if (session.status !== 'authenticated') {
    throw new Error('Expected authenticated session bootstrap.');
  }
  assert.equal(session.user.activeHouseholdId, 'household-abc');
  assert.equal(session.user.households[0]?.householdName, 'Primary Household');
});

test('fetchSession maps 401 bootstrap failures to unauthenticated state', async () => {
  globalThis.fetch = (async () =>
    jsonResponse(401, {
      detail: {
        code: 'unauthenticated',
        message: 'No authenticated household session was resolved for this request.',
      },
    })) as typeof fetch;

  const session = await fetchSession();

  assert.deepEqual(session, {
    status: 'unauthenticated',
    message: 'No authenticated household session was resolved for this request.',
  });
});

test('fetchSession maps 403 bootstrap failures to unauthorized state', async () => {
  globalThis.fetch = (async () =>
    jsonResponse(403, {
      detail: {
        code: 'household_access_forbidden',
        message: "The active household selected for this request is not one of the caller's memberships.",
      },
    })) as typeof fetch;

  const session = await fetchSession();

  assert.deepEqual(session, {
    status: 'unauthorized',
    message: "The active household selected for this request is not one of the caller's memberships.",
  });
});

