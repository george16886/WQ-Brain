document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('data-target');
            
            navItems.forEach(n => n.classList.remove('active'));
            views.forEach(v => {
                v.classList.remove('active');
                v.style.display = 'none';
            });
            
            item.classList.add('active');
            const targetView = document.getElementById(targetId);
            targetView.style.display = 'flex';
            
            // Allow animation to trigger
            setTimeout(() => {
                targetView.classList.add('active');
            }, 10);
        });
    });

    // Toast logic
    const showToast = (message) => {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    };

    // Load Data
    const loadAlphas = async () => {
        const res = await fetch('/api/alphas');
        const data = await res.json();
        document.getElementById('alphas-editor').value = data.content;
    };

    const loadSettings = async () => {
        const res = await fetch('/api/settings');
        const data = await res.json();
        if(data.settings) {
            document.getElementById('global-universe').value = data.settings.universe;
            document.getElementById('global-neutralization').value = data.settings.neutralization;
            document.getElementById('global-delay').value = data.settings.delay;
            document.getElementById('global-decay').value = data.settings.decay;
            document.getElementById('global-truncation').value = data.settings.truncation;
        }
        if(data.enable_sweep !== undefined) {
            document.getElementById('enable-sweep').checked = data.enable_sweep;
        }
        if(data.sweep_mode) {
            document.getElementById('sweep-mode').value = data.sweep_mode;
        }
    };

    const loadStats = async () => {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('stat-alphas').textContent = data.alphas;
            document.getElementById('stat-sims').textContent = data.simulations;
            
            // update progress denominator if not currently running
            if (badge.textContent !== 'RUNNING') {
                document.getElementById('stat-progress').textContent = `0 / ${data.simulations}`;
            }
        } catch(e) {
            console.error("Failed to load stats:", e);
        }
    };

    loadAlphas();
    loadSettings();
    
    // We need to make sure badge is defined before loadStats uses it
    const badge = document.getElementById('status-badge');
    loadStats();

    // Save Alphas
    const saveAlphas = async () => {
        const content = document.getElementById('alphas-editor').value;
        await fetch('/api/alphas', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content })
        });
        showToast('Alphas saved successfully!');
        await loadStats();
    };

    document.getElementById('save-alphas-btn').addEventListener('click', saveAlphas);

    // Save Settings
    const saveSettings = async () => {
        // First get current settings to preserve sweep_params
        const res = await fetch('/api/settings');
        const currentData = await res.json();

        const payload = {
            settings: {
                universe: document.getElementById('global-universe').value,
                neutralization: document.getElementById('global-neutralization').value,
                delay: parseInt(document.getElementById('global-delay').value),
                decay: parseInt(document.getElementById('global-decay').value),
                truncation: parseFloat(document.getElementById('global-truncation').value)
            },
            enable_sweep: document.getElementById('enable-sweep').checked,
            sweep_mode: document.getElementById('sweep-mode').value,
            sweep_params: currentData.sweep_params || {}
        };

        await fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        showToast('Settings saved successfully!');
        await loadStats();
    };

    document.getElementById('save-settings-btn').addEventListener('click', saveSettings);

    // Run Simulation
    let logInterval = null;
    const terminal = document.getElementById('terminal-output');

    const fetchLogs = async () => {
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            
            // update progress
            if (badge.textContent === 'RUNNING') {
                const totalSims = parseInt(document.getElementById('stat-sims').textContent) || 0;
                // Count how many "Result added to CSV!" are in the log content
                const doneCount = (data.content.match(/Result added to CSV!/g) || []).length;
                document.getElementById('stat-progress').textContent = `${doneCount} / ${totalSims}`;
                
                if (totalSims > 0 && doneCount >= totalSims) {
                    badge.className = 'badge idle';
                    badge.textContent = 'DONE';
                    document.getElementById('run-btn').style.display = 'block';
                    document.getElementById('stop-btn').style.display = 'none';
                }
            }
            
            // Escape HTML safely
            const escapeHTML = str => str.replace(/[&<>'"]/g, tag => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
            }[tag] || tag));
            
            let safeContent = escapeHTML(data.content);
            
            // Linkify URLs
            const urlRegex = /(https?:\/\/[^\s]+)/g;
            safeContent = safeContent.replace(urlRegex, '<a href="$1" target="_blank" style="color: #60a5fa; text-decoration: underline;">$1</a>');
            
            terminal.innerHTML = safeContent;
            terminal.scrollTop = terminal.scrollHeight;
        } catch(e) {}
    };

    document.getElementById('run-btn').addEventListener('click', async () => {
        
        terminal.textContent = "Saving configurations...\n";
        try {
            await saveAlphas();
            await saveSettings();
        } catch(e) {
            console.error("Failed to save before running:", e);
        }

        // Switch to terminal view
        navItems[2].click();
        
        terminal.textContent += "Initializing simulation...\n";
        badge.className = 'badge running';
        badge.textContent = 'RUNNING';
        
        document.getElementById('run-btn').style.display = 'none';
        document.getElementById('stop-btn').style.display = 'block';

        try {
            await fetch('/api/run', { method: 'POST' });
            
            // Poll for logs every 2 seconds
            if(logInterval) clearInterval(logInterval);
            logInterval = setInterval(fetchLogs, 2000);
            
        } catch(e) {
            terminal.textContent += "\nFailed to start simulation.";
            badge.className = 'badge idle';
            badge.textContent = 'ERROR';
            document.getElementById('run-btn').style.display = 'block';
            document.getElementById('stop-btn').style.display = 'none';
        }
    });

    document.getElementById('stop-btn').addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
            badge.className = 'badge idle';
            badge.textContent = 'STOPPED';
            terminal.textContent += "\nSimulation stopped by user.\n";
        } catch(e) {
            console.error(e);
        } finally {
            document.getElementById('run-btn').style.display = 'block';
            document.getElementById('stop-btn').style.display = 'none';
        }
    });

    document.getElementById('shutdown-server-btn').addEventListener('click', async () => {
        if (confirm("Are you sure you want to stop the server?")) {
            try {
                await fetch('/api/shutdown', { method: 'POST' });
                document.body.innerHTML = "<div style='display: flex; justify-content: center; align-items: center; height: 100vh; color: white; font-size: 1.5em; background: rgba(0,0,0,0.8);'>Server has been stopped. You can close this window.</div>";
            } catch(e) {
                console.error(e);
            }
        }
    });
});
