import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext({});

function isGoogleSession(session) {
  if (!session?.user?.identities?.some(identity => identity.provider === 'google')) return false;
  try {
    const payload = session.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(payload)).amr?.some(entry => entry.method === 'oauth') === true;
  } catch {
    return false;
  }
}

export const AuthProvider = ({ children }) => {
  const [googleSession, setGoogleSession] = useState(false);
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    let active = true;
    let currentId = null;
    let generation = 0;
    const fetchProfile = async userId => {
      const version = ++generation;
      try {
        const { data, error } = await supabase.from('profiles').select('*').eq('id', userId).single();
        if (active && currentId === userId && version === generation) setProfile(error ? null : data);
      } catch {
        if (active && currentId === userId && version === generation) setProfile(null);
      } finally {
        if (active && version === generation) setLoading(false);
      }
    };
    const update = session => {
      if (!active) return;
      const nextId = session?.user?.id ?? null;
      if (currentId !== nextId) { setProfile(null); setLoading(!!nextId); }
      currentId = nextId;
      setUser(session?.user ?? null);
      setGoogleSession(isGoogleSession(session));
      if (nextId) {
        // Supabase calls must run outside the Auth callback's internal lock.
        setTimeout(() => { if (active && currentId === nextId) fetchProfile(nextId); }, 0);
      } else { ++generation; setProfile(null); setLoading(false); }
      setInitialized(true);
    };
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => update(session));
    const refresh = () => { if (active && currentId && !document.hidden) fetchProfile(currentId); };
    const timer = setInterval(refresh, 30000);
    window.addEventListener('focus', refresh);
    return () => { active = false; subscription.unsubscribe(); clearInterval(timer); window.removeEventListener('focus', refresh); };
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        googleSession,
        profile,
        loading,
        isProfessor: profile?.papel === 'professor',
        isAdmin: profile?.papel === 'admin',
        signOut,
      }}
    >
      {initialized && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
