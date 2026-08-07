import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ModuleId } from '../types';
import {
  AuthUser,
  getAuthToken,
  setAuthToken,
  loginRequest,
  logoutRequest,
  fetchCurrentUser,
  fetchUsers,
  createUserRequest,
  updateUserRequest,
  resetPasswordRequest,
  deleteUserRequest,
  impersonateRequest,
  uploadAvatarImageRequest,
  removeAvatarImageRequest,
} from '../services/api';

// Re-exportado por compatibilidad -- otros archivos importan este nombre.
export type UserProfile = AuthUser;

interface UserContextType {
  currentUser: UserProfile | null;
  users: UserProfile[];
  isLoadingSession: boolean;
  isModuleAllowed: (moduleId: ModuleId, user?: UserProfile) => boolean;

  login: (email: string, password: string) => Promise<UserProfile>;
  logout: () => void;

  // Gestión de usuarios (solo Administrador -- el backend lo valida igual,
  // esto es solo para que la UI no ofrezca acciones que van a fallar)
  refreshUsers: () => Promise<void>;
  addUser: (newUser: { email: string; nombre: string; rol: string; password: string; blockedModules?: ModuleId[]; allowedModulesOnly?: ModuleId[] }) => Promise<void>;
  updateUser: (userId: string, changes: Partial<Pick<UserProfile, 'nombre' | 'rol' | 'avatarColor'>> & { avatarIcon?: string; blockedModules?: ModuleId[]; allowedModulesOnly?: ModuleId[] }) => Promise<void>;
  uploadAvatarImage: (userId: string, file: File) => Promise<void>;
  removeAvatarImage: (userId: string) => Promise<void>;
  resetUserPassword: (userId: string, newPassword: string) => Promise<void>;
  removeUser: (userId: string) => Promise<void>;
  impersonate: (targetUserId: string) => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [isLoadingSession, setIsLoadingSession] = useState(true);

  // Al montar: si hay un token guardado, valida la sesión contra el
  // backend (GET /api/auth/me) en vez de confiar ciegamente en lo que
  // haya en localStorage.
  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setIsLoadingSession(false);
      return;
    }
    fetchCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => {
        // Token inválido o expirado -- limpia y vuelve a pedir login.
        setAuthToken(null);
        setCurrentUser(null);
      })
      .finally(() => setIsLoadingSession(false));
  }, []);

  // Refresca la lista de usuarios solo cuando el usuario actual es Admin
  // (el backend igual la bloquearía para otros roles).
  useEffect(() => {
    if (currentUser?.rol === 'Administrador') {
      fetchUsers().then(setUsers).catch(() => setUsers([]));
    } else {
      setUsers(currentUser ? [currentUser] : []);
    }
  }, [currentUser]);

  const isModuleAllowed = (moduleId: ModuleId, userToTest?: UserProfile): boolean => {
    const targetUser = userToTest || currentUser;
    if (!targetUser) return false;

    if (moduleId === 'pendientes_despacho' && targetUser.nombre !== 'William Garrido') {
      return false;
    }

    if (targetUser.allowedModulesOnly && targetUser.allowedModulesOnly.length > 0) {
      return targetUser.allowedModulesOnly.includes(moduleId);
    }
    return !targetUser.blockedModules.includes(moduleId);
  };

  const login = async (email: string, password: string): Promise<UserProfile> => {
    const { token, user } = await loginRequest(email, password);
    setAuthToken(token);
    setCurrentUser(user);
    return user;
  };

  const logout = () => {
    logoutRequest().catch(() => {
      // Si falla la llamada de logout (ej. red caída), igual limpiamos la
      // sesión localmente -- no tiene sentido dejar al usuario "atascado".
    });
    setAuthToken(null);
    setCurrentUser(null);
    setUsers([]);
  };

  const refreshUsers = async () => {
    const list = await fetchUsers();
    setUsers(list);
  };

  const addUser: UserContextType['addUser'] = async (newUser) => {
    await createUserRequest(newUser);
    await refreshUsers();
  };

  const updateUser: UserContextType['updateUser'] = async (userId, changes) => {
    const updated = await updateUserRequest(userId, changes);
    // refreshUsers() llama a GET /api/auth/users, que el backend restringe
    // a rol Administrador -- si quien cambia su propio avatar NO es admin,
    // llamar refreshUsers() acá le devolvería un 403 innecesario. En ese
    // caso actualizamos localmente en vez de recargar todo desde el server.
    if (currentUser?.rol === 'Administrador') {
      await refreshUsers();
    } else {
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    }
    if (currentUser?.id === userId) setCurrentUser(updated);
  };

  const uploadAvatarImage = async (userId: string, file: File) => {
    const updated = await uploadAvatarImageRequest(userId, file);
    if (currentUser?.rol === 'Administrador') {
      await refreshUsers();
    } else {
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    }
    if (currentUser?.id === userId) setCurrentUser(updated);
  };

  const removeAvatarImage = async (userId: string) => {
    const updated = await removeAvatarImageRequest(userId);
    if (currentUser?.rol === 'Administrador') {
      await refreshUsers();
    } else {
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    }
    if (currentUser?.id === userId) setCurrentUser(updated);
  };

  const resetUserPassword = async (userId: string, newPassword: string) => {
    await resetPasswordRequest(userId, newPassword);
  };

  const removeUser = async (userId: string) => {
    await deleteUserRequest(userId);
    await refreshUsers();
  };

  const impersonate = async (targetUserId: string) => {
    const { token, user } = await impersonateRequest(targetUserId);
    setAuthToken(token);
    setCurrentUser(user);
  };

  return (
    <UserContext.Provider
      value={{
        currentUser,
        users,
        isLoadingSession,
        isModuleAllowed,
        login,
        logout,
        refreshUsers,
        addUser,
        updateUser,
        uploadAvatarImage,
        removeAvatarImage,
        resetUserPassword,
        removeUser,
        impersonate,
      }}
    >
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
