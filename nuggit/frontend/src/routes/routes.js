// src/routes/routes.js

import Home from './Home.svelte';
import Detail from './Detail.svelte';

export default {
  '/': Home,
  '/repo/:id': Detail
};

