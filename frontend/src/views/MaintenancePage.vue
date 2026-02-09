<template>
  <div class="maintenance-page">
    <div class="maintenance-container">
      <div class="logo-section">
        <div class="logo">
          <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1 class="brand">GitSight</h1>
      </div>
      
      <div class="content-section">
        <div class="icon-container">
          <svg class="wrench-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        
        <h2 class="title">Under Maintenance</h2>
        
        <p class="description">
          We're upgrading GitSight to serve you better. 
          Our team is working hard to bring you an improved experience.
        </p>
        
        <div class="status-card">
          <div class="status-item">
            <span class="status-dot"></span>
            <span>System Upgrade in Progress</span>
          </div>
          <div class="estimated-time">
            <svg class="clock-icon" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>We'll be back soon!</span>
          </div>
        </div>
        
        <div class="social-links">
          <a href="https://github.com/Saail289/GITSIGHT" target="_blank" class="social-btn">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            View on GitHub
          </a>
        </div>
      </div>
      
      <div class="footer">
        <p>&copy; 2026 GitSight. All rights reserved.</p>
      </div>
    </div>
    
    <!-- Background Animation -->
    <div class="bg-animation">
      <div class="particle"></div>
      <div class="particle"></div>
      <div class="particle"></div>
      <div class="particle"></div>
      <div class="particle"></div>
    </div>
  </div>
</template>

<script setup>
// Maintenance page - no logic needed
</script>

<style scoped>
.maintenance-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0a0f0a 0%, #1a2f1a 50%, #0a1a0a 100%);
  position: relative;
  overflow: hidden;
}

.maintenance-container {
  text-align: center;
  padding: 3rem 2rem;
  max-width: 500px;
  z-index: 10;
}

.logo-section {
  margin-bottom: 2rem;
}

.logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-radius: 20px;
  color: white;
  margin-bottom: 1rem;
  box-shadow: 0 10px 40px rgba(34, 197, 94, 0.3);
}

.brand {
  font-size: 2.5rem;
  font-weight: 700;
  color: #22c55e;
  margin: 0;
  letter-spacing: -1px;
}

.content-section {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 24px;
  padding: 2.5rem;
  margin-bottom: 2rem;
}

.icon-container {
  margin-bottom: 1.5rem;
}

.wrench-icon {
  width: 64px;
  height: 64px;
  color: #22c55e;
  animation: wiggle 2s ease-in-out infinite;
}

@keyframes wiggle {
  0%, 100% { transform: rotate(-10deg); }
  50% { transform: rotate(10deg); }
}

.title {
  font-size: 1.75rem;
  font-weight: 600;
  color: #fff;
  margin: 0 0 1rem 0;
}

.description {
  color: rgba(255, 255, 255, 0.7);
  font-size: 1rem;
  line-height: 1.6;
  margin: 0 0 1.5rem 0;
}

.status-card {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.status-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #22c55e;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  background: #22c55e;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.estimated-time {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
}

.clock-icon {
  width: 18px;
  height: 18px;
}

.social-links {
  display: flex;
  justify-content: center;
}

.social-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.social-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(34, 197, 94, 0.5);
  color: #22c55e;
  transform: translateY(-2px);
}

.social-btn svg {
  width: 20px;
  height: 20px;
}

.footer {
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.85rem;
}

/* Background Animation */
.bg-animation {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(34, 197, 94, 0.5);
  border-radius: 50%;
  animation: float 15s infinite;
}

.particle:nth-child(1) { left: 10%; animation-delay: 0s; }
.particle:nth-child(2) { left: 30%; animation-delay: 3s; }
.particle:nth-child(3) { left: 50%; animation-delay: 6s; }
.particle:nth-child(4) { left: 70%; animation-delay: 9s; }
.particle:nth-child(5) { left: 90%; animation-delay: 12s; }

@keyframes float {
  0%, 100% {
    transform: translateY(100vh) scale(0);
    opacity: 0;
  }
  10% {
    opacity: 1;
    transform: translateY(80vh) scale(1);
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-10vh) scale(0.5);
    opacity: 0;
  }
}
</style>
