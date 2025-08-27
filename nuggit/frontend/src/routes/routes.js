// src/routes/routes.js

import Landing from './Landing.svelte';
import Home from './Home.svelte';
import Detail from './Detail.svelte';
import Admin from './Admin.svelte';
import Profile from './Profile.svelte';
import Settings from './Settings.svelte';

// Authentication components
import Login from '../components/auth/Login.svelte';
import Register from '../components/auth/Register.svelte';
import VerifyEmail from '../components/auth/VerifyEmail.svelte';

// Route guards
import { requireAuth, requireAdmin, requireGuest } from '../lib/auth/authGuard.js';

export default {
  // Public routes
  '/': Landing,
  '/home': Home,

  // Authentication routes
  '/login': Login,
  '/register': Register,
  '/verify-email': VerifyEmail,

  // Protected routes
  '/repo/:id': Detail,
  '/profile': Profile,
  '/settings': Settings,

  // Admin routes
  '/admin': Admin,

  // Catch-all route for 404
  '*': Landing
};

