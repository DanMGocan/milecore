import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

export function useAuth() {
    return useContext(AuthContext);
}

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);         // { id, email, display_name }
    const [instances, setInstances] = useState([]);   // [{ id, name, slug, role }]
    const [loading, setLoading] = useState(true);     // true while checking auth on mount
    const [instanceId, setInstanceId] = useState(() => {
        // Read from cookie
        const match = document.cookie.match(/(?:^|;\s*)instance_id=(\d+)/);
        return match ? Number(match[1]) : null;
    });

    const currentInstance = instances.find(i => i.id === instanceId) || null;
    const isAuthenticated = !!user;

    const checkAuth = useCallback(async () => {
        try {
            const res = await fetch('/api/auth/me', { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setUser(data.user);
                const userInstances = data.instances || [];
                setInstances(userInstances);

                // Clear stale instance_id cookie if it doesn't match any membership
                setInstanceId(prev => {
                    if (prev && !userInstances.some(i => i.id === prev)) {
                        document.cookie = 'instance_id=; path=/; max-age=0';
                        return null;
                    }
                    return prev;
                });
            } else {
                setUser(null);
                setInstances([]);
            }
        } catch {
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { checkAuth(); }, [checkAuth]);

    const login = async (email, password) => {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
            credentials: 'include',
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Login failed');
        await checkAuth();
        return data;
    };

    const signup = async (email, password, displayName) => {
        const res = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, display_name: displayName }),
            credentials: 'include',
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Signup failed');
        await checkAuth();
        return data;
    };

    const logout = async () => {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
        setUser(null);
        setInstances([]);
        setInstanceId(null);
    };

    const selectInstance = async (id) => {
        const res = await fetch(`/api/instances/${id}/select`, {
            method: 'POST',
            credentials: 'include',
        });
        if (res.ok) {
            setInstanceId(id);
        }
    };

    const refreshInstances = async () => {
        try {
            const res = await fetch('/api/instances', { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setInstances(data.instances || []);
            }
        } catch {}
    };

    return (
        <AuthContext.Provider value={{
            user, instances, instanceId, currentInstance,
            isAuthenticated, loading,
            login, signup, logout, selectInstance, refreshInstances, checkAuth,
        }}>
            {children}
        </AuthContext.Provider>
    );
}
