// src/routes/routes.js

import Landing from './Landing.svelte';
import Home from './Home.svelte';
import Detail from './Detail.svelte';
import Admin from './Admin.svelte';

// Authentication components
import Login from '../components/auth/Login.svelte';
import Register from '../components/auth/Register.svelte';

// Route guards
import { requireAuth, requireAdmin, requireGuest } from '../lib/auth/authGuard.js';

export default {
  // Public routes
  '/': Landing,
  '/home': requireAuth(Home),

  // Authentication routes (guest only)
  '/login': requireGuest(Login),
  '/register': requireGuest(Register),

  // Protected routes (authentication required)
  '/repo/:id': requireAuth(Detail),

  // Admin routes (admin privileges required)
  '/admin': requireAdmin(Admin),

  // Catch-all route for 404
  '*': Landing
};

