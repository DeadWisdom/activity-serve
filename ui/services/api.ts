import { getCurrentUser, getToken } from './auth';

export interface FetchOptions extends RequestInit {
  // Add any custom options here if needed
}

export async function fetchAPI(path: string, options: FetchOptions = {}): Promise<any> {
  let token = await getToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  let headers = { 'Authorization': `Bearer ${token}` };
  if (options.headers) {
    options.headers = { ...options.headers, ...headers };
  } else {
    options.headers = headers;
  }

  let response = await fetch(path, options);
  if (!response.ok) {
    console.error('API request failed:', response.statusText);
    console.log(await response.text())
    return response;
  }

  return await response.json();
}


export async function getMe(): Promise<any | null> {
  const user = getCurrentUser();
  if (!user) return null;

  return await fetchAPI('/me');
}

export async function getCollection(path: string): Promise<any> {
  return await fetchAPI(path);
}

export async function postToOutbox(activity: any): Promise<any> {
  let me = await getMe();
  return await fetchAPI(me.outbox, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(activity),
  });
}

export async function getOutbox(): Promise<any> {
  let me = await getMe();
  if (!me || !me.outbox) return null;
  return await fetchAPI(me.outbox);
}

export async function getInbox(): Promise<any> {
  let me = await getMe();
  if (!me || !me.inbox) return null;
  return await fetchAPI(me.inbox);
}

//@ts-ignore
window.postToOutbox = postToOutbox;