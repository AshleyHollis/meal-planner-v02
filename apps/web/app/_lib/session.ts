import { api, ApiError } from './api';
import type {
  HouseholdMembership,
  HouseholdRole,
  SessionState,
  SessionResponse,
  SessionUser,
} from './types';

export type { SessionUser };

type ApiHouseholdMembership = {
  household_id?: string;
  household_name?: string;
  role?: HouseholdRole;
};

type ApiSessionUser = {
  user_id?: string;
  userId?: string;
  email?: string;
  display_name?: string;
  displayName?: string;
  active_household_id?: string;
  activeHouseholdId?: string;
  households?: ApiHouseholdMembership[];
  householdId?: string;
  householdName?: string;
  role?: HouseholdRole;
};

type ApiSessionResponse = {
  authenticated?: boolean;
  user?: ApiSessionUser | null;
};

function isSessionResponse(value: ApiSessionResponse | ApiSessionUser): value is ApiSessionResponse {
  return 'authenticated' in value;
}

function normalizeMembership(
  household: ApiHouseholdMembership | undefined,
  fallbackId?: string,
  fallbackName?: string,
  fallbackRole?: HouseholdRole
): HouseholdMembership | null {
  const householdId = household?.household_id ?? fallbackId;
  if (!householdId) {
    return null;
  }

  return {
    householdId,
    householdName: household?.household_name ?? fallbackName ?? 'Household',
    role: household?.role ?? fallbackRole ?? 'member',
  };
}

function normalizeUser(raw: ApiSessionUser): SessionUser | null {
  const memberships = (raw.households ?? [])
    .map((membership) => normalizeMembership(membership))
    .filter((membership): membership is HouseholdMembership => membership !== null);

  const activeHouseholdId = raw.active_household_id ?? raw.activeHouseholdId ?? raw.householdId;
  const fallbackMembership = normalizeMembership(
    undefined,
    activeHouseholdId,
    raw.householdName,
    raw.role
  );

  const primaryHousehold =
    memberships.find((membership) => membership.householdId === activeHouseholdId) ??
    fallbackMembership ??
    memberships[0];
  if (!primaryHousehold) {
    return null;
  }

  const allMemberships = [
    primaryHousehold,
    ...memberships.filter(
      (membership) => membership.householdId !== primaryHousehold.householdId
    ),
  ];

  return {
    userId: raw.user_id ?? raw.userId ?? '',
    email: raw.email ?? '',
    displayName: raw.display_name ?? raw.displayName ?? raw.email ?? 'Meal Planner User',
    activeHouseholdId: primaryHousehold.householdId,
    activeHouseholdName: primaryHousehold.householdName,
    activeHouseholdRole: primaryHousehold.role,
    householdId: primaryHousehold.householdId,
    householdName: primaryHousehold.householdName,
    role: primaryHousehold.role,
    households: allMemberships,
  };
}

function sessionMessage(detail: unknown, fallback: string): string {
  if (
    detail &&
    typeof detail === 'object' &&
    'message' in detail &&
    typeof detail.message === 'string' &&
    detail.message.trim()
  ) {
    return detail.message;
  }

  return fallback;
}

export async function fetchSession(): Promise<SessionState> {
  try {
    const response = await api.get<ApiSessionResponse | ApiSessionUser>('/api/v1/me');

    if (isSessionResponse(response)) {
      if (!response.authenticated || !response.user) {
        return {
          status: 'unauthenticated',
          message: 'Sign in to load your household session.',
        };
      }

      const user = normalizeUser(response.user);
      if (!user) {
        return {
          status: 'unauthorized',
          message: 'Your session does not include an active household membership.',
        };
      }

      return { status: 'authenticated', user };
    }

    const user = normalizeUser(response);
    if (!user) {
      return {
        status: 'unauthorized',
        message: 'Your session does not include an active household membership.',
      };
    }

    return { status: 'authenticated', user };
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return {
        status: 'unauthenticated',
        message: sessionMessage(err.detail, 'Sign in to load your household session.'),
      };
    }

    if (err instanceof ApiError && err.status === 403) {
      return {
        status: 'unauthorized',
        message: sessionMessage(
          err.detail,
          'This session is not allowed to access the active household.'
        ),
      };
    }

    throw err;
  }
}

export function toSessionResponse(user: SessionUser | null): SessionResponse {
  return {
    authenticated: Boolean(user),
    user,
  };
}
