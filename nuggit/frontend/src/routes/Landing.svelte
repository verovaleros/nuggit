<!--
  Landing Page Component for Nuggit
  
  Introduces users to Nuggit's features and benefits before they sign up.
  Includes hero section, features, benefits, and call-to-action.
-->

<script>
  import { push } from 'svelte-spa-router';
  import { authStore } from '../lib/stores/authStore.js';

  // Auth state
  $: authState = $authStore;
  $: if (authState.isAuthenticated) {
    // Redirect to home if already authenticated
    push('/home');
  }

  // Navigation functions are no longer needed since we're using anchor tags

  // Feature data
  const features = [
    {
      icon: '🧠',
      title: 'Smart Repository Tracking',
      description: 'Automatically sync and track your GitHub repositories with real-time updates on stars, forks, commits, and more.'
    },
    {
      icon: '📊',
      title: 'Comprehensive Analytics',
      description: 'Get detailed insights into your repository performance, growth trends, and community engagement metrics.'
    },
    {
      icon: '🏷️',
      title: 'Intelligent Organization',
      description: 'Tag and categorize your repositories with custom labels, notes, and smart filtering for easy management.'
    },
    {
      icon: '📈',
      title: 'Version Tracking',
      description: 'Track changes over time with automatic version snapshots and compare repository metrics across different periods.'
    },
    {
      icon: '💬',
      title: 'Collaborative Comments',
      description: 'Add timestamped comments and notes to repositories for team collaboration and project documentation.'
    },
    {
      icon: '🔄',
      title: 'Batch Operations',
      description: 'Import multiple repositories at once and apply bulk operations like tagging and organization efficiently.'
    }
  ];

  const benefits = [
    {
      title: 'Save Time',
      description: 'Stop manually checking each repository. Get all your GitHub data in one organized dashboard.',
      icon: '⏰'
    },
    {
      title: 'Stay Organized',
      description: 'Keep track of hundreds of repositories with smart tagging, filtering, and search capabilities.',
      icon: '📁'
    },
    {
      title: 'Track Growth',
      description: 'Monitor your open source impact with detailed analytics and historical data tracking.',
      icon: '📈'
    },
    {
      title: 'Collaborate Better',
      description: 'Share insights with your team using comments, notes, and organized repository collections.',
      icon: '🤝'
    }
  ];
</script>

<div class="landing-container">
  <!-- Hero Section -->
  <section class="hero">
    <div class="hero-content">
      <div class="hero-text">
        <h1 class="hero-title">
          <span class="brand">🧠 Nuggit</span>
          <span class="tagline">Your GitHub Repository Intelligence Platform</span>
        </h1>
        <p class="hero-description">
          Transform how you manage and understand your GitHub repositories. 
          Nuggit provides powerful analytics, smart organization, and collaborative tools 
          to help developers and teams maximize their open source impact.
        </p>
        <div class="hero-actions">
          <a
            href="#/register"
            class="cta-primary"
            role="button"
          >
            🚀 Get Started Free
          </a>
          <a
            href="#/login"
            class="cta-secondary"
            role="button"
          >
            Sign In
          </a>
        </div>
        <p class="hero-note">
          ✨ No credit card required • Free for individual developers
        </p>


      </div>
      <div class="hero-visual">
        <div class="dashboard-preview">
          <div class="preview-header">
            <div class="preview-dots">
              <span class="dot red"></span>
              <span class="dot yellow"></span>
              <span class="dot green"></span>
            </div>
            <span class="preview-title">Nuggit Dashboard</span>
          </div>
          <div class="preview-content">
            <div class="preview-stats">
              <div class="stat-card">
                <span class="stat-number">199</span>
                <span class="stat-label">Repositories</span>
              </div>
              <div class="stat-card">
                <span class="stat-number">12.5K</span>
                <span class="stat-label">Total Stars</span>
              </div>
              <div class="stat-card">
                <span class="stat-number">3.2K</span>
                <span class="stat-label">Forks</span>
              </div>
            </div>
            <div class="preview-repos">
              <div class="repo-item">
                <span class="repo-name">awesome-project</span>
                <span class="repo-stars">⭐ 1.2K</span>
              </div>
              <div class="repo-item">
                <span class="repo-name">ml-toolkit</span>
                <span class="repo-stars">⭐ 856</span>
              </div>
              <div class="repo-item">
                <span class="repo-name">web-components</span>
                <span class="repo-stars">⭐ 432</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Features Section -->
  <section class="features">
    <div class="section-content">
      <h2 class="section-title">Powerful Features for Modern Developers</h2>
      <p class="section-description">
        Everything you need to manage, analyze, and grow your GitHub presence
      </p>
      
      <div class="features-grid">
        {#each features as feature}
          <div class="feature-card">
            <div class="feature-icon">{feature.icon}</div>
            <h3 class="feature-title">{feature.title}</h3>
            <p class="feature-description">{feature.description}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- Benefits Section -->
  <section class="benefits">
    <div class="section-content">
      <h2 class="section-title">Why Choose Nuggit?</h2>
      
      <div class="benefits-grid">
        {#each benefits as benefit}
          <div class="benefit-card">
            <div class="benefit-icon">{benefit.icon}</div>
            <h3 class="benefit-title">{benefit.title}</h3>
            <p class="benefit-description">{benefit.description}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- CTA Section -->
  <section class="cta-section">
    <div class="cta-content">
      <h2 class="cta-title">Ready to Transform Your GitHub Workflow?</h2>
      <p class="cta-description">
        Join thousands of developers who use Nuggit to manage their repositories more effectively
      </p>
      <div class="cta-actions">
        <a
          href="#/register"
          class="cta-primary large"
          role="button"
        >
          🚀 Start Your Free Account
        </a>
      </div>
      <p class="cta-note">
        Free forever for individual developers • No setup required
      </p>
    </div>
  </section>

  <!-- Footer -->
  <footer class="landing-footer">
    <div class="footer-content">
      <div class="footer-brand">
        <span class="footer-logo">🧠 Nuggit</span>
        <p class="footer-tagline">GitHub Repository Intelligence Platform</p>
      </div>
      <div class="footer-links">
        <a href="#/login" class="footer-link">Sign In</a>
        <a href="#/register" class="footer-link">Sign Up</a>
      </div>
    </div>
  </footer>
</div>

<style>
  .landing-container {
    min-height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin-top: -60px; /* Offset the main-content padding-top */
  }

  /* Hero Section */
  .hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 4rem 2rem;
    min-height: 80vh;
    display: flex;
    align-items: center;
  }

  .hero-content {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4rem;
    align-items: center;
  }

  .hero-title {
    font-size: 3.5rem;
    font-weight: 700;
    margin: 0 0 1.5rem 0;
    line-height: 1.1;
  }

  .brand {
    display: block;
    font-size: 4rem;
    margin-bottom: 0.5rem;
  }

  .tagline {
    display: block;
    font-size: 2.5rem;
    font-weight: 600;
    opacity: 0.95;
  }

  .hero-description {
    font-size: 1.25rem;
    line-height: 1.6;
    margin: 0 0 2rem 0;
    opacity: 0.9;
  }

  .hero-actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .cta-primary {
    background: white;
    color: #667eea;
    border: none;
    padding: 1rem 2rem;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .cta-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  }

  .cta-primary.large {
    padding: 1.25rem 2.5rem;
    font-size: 1.2rem;
  }

  .cta-secondary {
    background: transparent;
    color: white;
    border: 2px solid white;
    padding: 1rem 2rem;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .cta-secondary:hover {
    background: white;
    color: #667eea;
  }

  .hero-note {
    font-size: 0.9rem;
    opacity: 0.8;
    margin: 0;
  }

  /* Dashboard Preview */
  .dashboard-preview {
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    transform: perspective(1000px) rotateY(-5deg) rotateX(5deg);
  }

  .preview-header {
    background: #f8f9fa;
    padding: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border-bottom: 1px solid #e1e5e9;
  }

  .preview-dots {
    display: flex;
    gap: 0.5rem;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .dot.red { background: #ff5f57; }
  .dot.yellow { background: #ffbd2e; }
  .dot.green { background: #28ca42; }

  .preview-title {
    font-weight: 600;
    color: #333;
    font-size: 0.9rem;
  }

  .preview-content {
    padding: 1.5rem;
  }

  .preview-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .stat-card {
    text-align: center;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .stat-number {
    display: block;
    font-size: 1.5rem;
    font-weight: 700;
    color: #667eea;
  }

  .stat-label {
    display: block;
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.25rem;
  }

  .preview-repos {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .repo-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: #f8f9fa;
    border-radius: 6px;
  }

  .repo-name {
    font-weight: 500;
    color: #333;
  }

  .repo-stars {
    color: #666;
    font-size: 0.9rem;
  }

  /* Sections */
  .features, .benefits {
    padding: 5rem 2rem;
    background: white;
  }

  .benefits {
    background: #f8f9fa;
  }

  .section-content {
    max-width: 1200px;
    margin: 0 auto;
  }

  .section-title {
    font-size: 2.5rem;
    font-weight: 700;
    text-align: center;
    margin: 0 0 1rem 0;
    color: #333;
  }

  .section-description {
    font-size: 1.2rem;
    text-align: center;
    color: #666;
    margin: 0 0 3rem 0;
  }

  .features-grid, .benefits-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 2rem;
  }

  .feature-card, .benefit-card {
    background: white;
    padding: 2rem;
    border-radius: 16px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    text-align: center;
    transition: transform 0.2s ease;
  }

  .feature-card:hover, .benefit-card:hover {
    transform: translateY(-4px);
  }

  .feature-icon, .benefit-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .feature-title, .benefit-title {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0 0 1rem 0;
    color: #333;
  }

  .feature-description, .benefit-description {
    color: #666;
    line-height: 1.6;
    margin: 0;
  }

  /* CTA Section */
  .cta-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 4rem 2rem;
    text-align: center;
  }

  .cta-content {
    max-width: 800px;
    margin: 0 auto;
  }

  .cta-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0 0 1rem 0;
  }

  .cta-description {
    font-size: 1.2rem;
    margin: 0 0 2rem 0;
    opacity: 0.9;
  }

  .cta-actions {
    margin-bottom: 1rem;
  }

  .cta-note {
    font-size: 0.9rem;
    opacity: 0.8;
    margin: 0;
  }

  /* Footer */
  .landing-footer {
    background: #333;
    color: white;
    padding: 2rem;
  }

  .footer-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .footer-logo {
    font-size: 1.5rem;
    font-weight: 700;
  }

  .footer-tagline {
    margin: 0.5rem 0 0 0;
    opacity: 0.8;
    font-size: 0.9rem;
  }

  .footer-links {
    display: flex;
    gap: 2rem;
  }

  .footer-link {
    color: white;
    text-decoration: none;
    opacity: 0.8;
    transition: opacity 0.2s ease;
  }

  .footer-link:hover {
    opacity: 1;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .hero-content {
      grid-template-columns: 1fr;
      gap: 2rem;
      text-align: center;
    }

    .hero-title {
      font-size: 2.5rem;
    }

    .brand {
      font-size: 3rem;
    }

    .tagline {
      font-size: 2rem;
    }

    .hero-actions {
      flex-direction: column;
      align-items: center;
    }

    .dashboard-preview {
      transform: none;
    }

    .features-grid, .benefits-grid {
      grid-template-columns: 1fr;
    }

    .footer-content {
      flex-direction: column;
      gap: 1rem;
      text-align: center;
    }

    .footer-links {
      justify-content: center;
    }
  }
</style>
