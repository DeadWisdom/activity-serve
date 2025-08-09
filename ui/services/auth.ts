import { initializeApp } from 'firebase/app';
import {
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth';

export { type User } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyD8WMf3nN-FrrT8LBYXhk9YxMaOjiBJS-g",
  authDomain: "share-the-plan.firebaseapp.com",
  projectId: "share-the-plan",
  storageBucket: "share-the-plan.firebasestorage.app",
  messagingSenderId: "686991090307",
  appId: "1:686991090307:web:29d10596aeaf75b7f271b6",
  measurementId: "G-9G73J4X8WT"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const providers = {
  google: new GoogleAuthProvider(),
};

export function subscribeAuth(callback: (user: User | null) => void) {
  return onAuthStateChanged(auth, callback);
}

export function getCurrentUser(): User | null {
  return auth.currentUser;
}

export async function signIn(providerName: string, extra: any) {
  await signInWithPopup(auth, providers[providerName as keyof typeof providers]);
  if (window.location.pathname === '/auth') {
    window.location.href = '/home';
  } else {
    window.location.reload();
  }
}

export async function signOut() {
  await firebaseSignOut(auth);
  window.location.href = '/auth';
}

export async function getToken() {
  const user = getCurrentUser();
  if (user) {
    return await user.getIdToken();
  }
  return null;
}

// @ts-ignore
globalThis.signIn = signIn;
// @ts-ignore
globalThis.signOut = signOut;
